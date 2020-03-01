import abc
import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime
from decimal import Decimal
from math import trunc
from typing import Optional, Dict, List

import token_bucket
from requests import PreparedRequest, Session
from requests.auth import AuthBase

from cloudwall.phemex.order import OrderPlacer, OrderPlaceable, OrderHandle, OrderFactory, LimitOrder, MarketOrder, \
    ConditionalOrder, Trigger, Order, TimeInForce


class PhemexCredentials(AuthBase):
    """
    Base class for public or private credentials.
    """

    @abc.abstractmethod
    def __call__(self, request: PreparedRequest):
        pass


class PublicCredentials(PhemexCredentials):
    """
    Public credentials are a no-op for request signing.
    """

    def __call__(self, request: PreparedRequest):
        return request


class AuthCredentials(PhemexCredentials):
    """
    Credentials for private API access.
    """

    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def __call__(self, request: PreparedRequest):
        expiry = str(trunc(time.time()) + 60)

        if '?' not in request.path_url:
            (url, query_string) = request.path_url, ''
        else:
            (url, query_string) = request.path_url.split('?')
        message = (url + query_string + expiry + (request.body or ''))
        message = message.encode('utf-8')
        hmac_key = base64.urlsafe_b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message, hashlib.sha256)
        signature_b64 = signature.hexdigest()
        request.headers.update({
            'x-phemex-request-signature': signature_b64,
            'x-phemex-request-expiry': expiry,
            'x-phemex-access-token': self.api_key,
            'Content-Type': 'application/json'
        })
        return request


class PhemexConnection:
    """
    Primary client entry point for Phemex API connection
    """

    def __init__(self, credentials: PhemexCredentials = PublicCredentials(), api_url='https://api.phemex.com',
                 request_timeout: int = 30, rate: float = 2.5, capacity: int = 200):
        self.credentials = credentials
        self.api_url = api_url.rstrip('/')
        self.request_timeout = request_timeout
        self.session = Session()
        self.storage = token_bucket.MemoryStorage()
        self.limiter = token_bucket.Limiter(rate, capacity, self.storage)

    def send_message(self, method: str, endpoint: str, params: Optional[Dict] = None,
                     data: Optional[str] = None):
        """
        Raw REST request message that sends a message to a given endpoint with optional parameters
        :return: JSON-encoded response
        """
        url = self.api_url + endpoint
        self.limiter.consume('phemex'.encode('UTF-8'), 1)
        r = self.session.request(method,
                                 url,
                                 params=params,
                                 data=data,
                                 auth=self.credentials,
                                 timeout=self.request_timeout)
        return r.json(parse_float=Decimal)

    def get_order_placer(self):
        return PhemexOrderPlacer(self)

    def get_products(self):
        return self.send_message('GET', '/exchange/public/products')

    def get_account_positions(self, currency: str):
        return self.send_message('GET', '/accounts/accountPositions', {'currency': currency})

    def get_trades(self, symbol: str, start_date: datetime, end_date: datetime):
        start_dt_millis = trunc(start_date.timestamp() * 1000)
        end_dt_millis = trunc(end_date.timestamp() * 1000)
        return self.send_message('GET', '/exchange/order/trade',
                                 {'symbol': symbol,
                                  'start': start_dt_millis,
                                  'end': end_dt_millis,
                                  'limit': 100, 'offset': 0,
                                  'withCount': True})


class CredentialError(Exception):
    """
    Exception raised when the API key lacks sufficient privileges to perform an action, e.g.
    you try and place an order using a ReadOnly API key.
    """
    def __init__(self):
        pass


class AuthenticationError(Exception):
    """
    Exception raised for more generic authentication problems.
    """
    def __init__(self):
        pass


class PhemexError(Exception):
    """
    Generic API for unhandled error codes.
    """
    def __init__(self, error_code: int):
        self.error_code = error_code

    def get_error_code(self) -> int:
        return self.error_code


class PhemexOrderHandle(OrderHandle):
    def __init__(self, order_placer: OrderPlacer, response):
        self.order_placer = order_placer
        self.symbol = response['data']['symbol']
        self.order_id = response['data']['orderID']

    def get_symbol(self) -> str:
        return self.symbol

    def get_order_id(self) -> str:
        return self.order_id

    def cancel(self):
        self.order_placer.cancel(self)


class PhemexOrderPlacer(OrderPlacer):
    """
    Implementation of an OrderPlacer for Phemex exchange.
    """

    def __init__(self, conn: PhemexConnection):
        super().__init__(OrderFactory())
        self.conn = conn

    def submit(self, op: OrderPlaceable) -> OrderHandle:
        params = dict()
        params['actionBy'] = 'FromOrderPlacement'
        params['clOrdID'] = str(uuid.uuid4())
        if isinstance(op, Order):
            params['symbol'] = op.get_contract().get_symbol()
            params['orderQty'] = op.get_qty()
            params['side'] = op.get_side().name.lower().capitalize()
            if isinstance(op, LimitOrder):
                params['ordType'] = 'Limit'
                params['priceEp'] = PhemexOrderPlacer.__get_scaled_price(op.get_price())
                params['timeInForce'] = PhemexOrderPlacer.__get_tif_code(op.get_time_in_force())
                params['reduceOnly'] = op.is_reduce_only()
            elif isinstance(op, MarketOrder):
                params['ordType'] = 'Market'
        elif isinstance(op, ConditionalOrder):
            cond_order = op.get_order()
            params['symbol'] = cond_order.get_contract().get_symbol()
            params['orderQty'] = cond_order.get_qty()
            params['side'] = cond_order.get_side().name.lower().capitalize()
            if isinstance(cond_order, LimitOrder):
                params['ordType'] = 'StopLimit'
                params['priceEp'] = PhemexOrderPlacer.__get_scaled_price(cond_order.get_price())
                params['timeInForce'] = PhemexOrderPlacer.__get_tif_code(cond_order.get_time_in_force())
                params['reduceOnly'] = cond_order.is_reduce_only()
            else:
                params['ordType'] = 'Stop'

            params['triggerType'] = PhemexOrderPlacer.__get_trigger_type_code(op.get_trigger())
            params['stopPxEp'] = PhemexOrderPlacer.__get_scaled_price(op.get_trigger_price())
            params['closeOnTrigger'] = op.is_close_on_trigger()
        else:
            raise ValueError(f'unsupported OrderPlaceable: {type(op)}')

        response = self.conn.send_message('POST', '/orders', data=json.dumps(params))
        error_code = int(response.get('code', 200))
        if error_code > 200:
            if error_code == 10500:
                raise AuthenticationError()
            elif error_code == 401:
                raise CredentialError()
            else:
                raise PhemexError(error_code)

        return PhemexOrderHandle(self, response)

    def cancel(self, handle: OrderHandle):
        if not isinstance(handle, PhemexOrderHandle):
            raise ValueError(f'unsupported OrderHandle type: {type(handle)}')
        symbol = handle.get_symbol()
        order_id = handle.get_order_id()
        self.conn.send_message('DELETE', '/orders', {
            'symbol': symbol,
            'orderID': order_id
        })

    def cancel_all(self, symbol: str):
        def do_cancel(untriggered: bool):
            self.conn.send_message('DELETE', '/orders', {
                'symbol': symbol,
                'untriggered': untriggered
            })
        do_cancel(True)
        do_cancel(False)

    @classmethod
    def __get_scaled_price(cls, price: float) -> int:
        return int(price * 10000)

    @classmethod
    def __get_trigger_type_code(cls, trigger: Trigger) -> str:
        if trigger == Trigger.LAST_PRICE:
            return 'ByLastPrice'
        elif trigger == Trigger.MARK_PRICE:
            return 'ByMarkPrice'
        else:
            raise ValueError(f'unsupported Trigger type: {trigger.name}')

    @classmethod
    def __get_tif_code(cls, tif: TimeInForce) -> str:
        if tif == TimeInForce.DAY:
            return 'Day'
        elif tif == TimeInForce.GTC:
            return 'GoodTillCancel'
        elif tif == TimeInForce.IOC:
            return 'ImmediateOrCancel'
        elif tif == TimeInForce.FOK:
            return 'FillOrKill'
        else:
            raise ValueError(f'unsupported TimeInForce: {tif.name}')
