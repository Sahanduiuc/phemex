import abc
import base64
import hashlib
import hmac
import time

from decimal import Decimal
from math import trunc
from requests import PreparedRequest, Session
from requests.auth import AuthBase
from typing import Optional, Dict


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
                 request_timeout: int = 30):
        self.credentials = credentials
        self.api_url = api_url.rstrip('/')
        self.request_timeout = request_timeout
        self.session = Session()

    def send_message(self, method: str, endpoint: str, params: Optional[Dict] = None,
                     data: Optional[str] = None):
        url = self.api_url + endpoint
        r = self.session.request(method,
                                 url,
                                 params=params,
                                 data=data,
                                 auth=self.credentials,
                                 timeout=self.request_timeout)
        return r.json(parse_float=Decimal)
