from abc import ABC, abstractmethod
from enum import Enum, auto


class Side(Enum):
    """
    Order side -- corresponds to long (buy) and short (sell) position.
    """
    BUY = auto()
    SELL = auto()


class TimeInForce(Enum):
    """
    Enumeration of supported TIF (time-in-force) values for the exchange.
    """
    DAY = auto()
    GTC = auto()
    IOC = auto()
    FOK = auto()


class Trigger(Enum):
    """
    Enumeration of supported trigger price types.
    """
    LAST_PRICE = auto()
    MARK_PRICE = auto()


class Contract:
    """
    Details of the perpetual contract to trade.
    """
    def __init__(self, symbol: str, leverage: int = 0):
        self.symbol = symbol
        self.leverage = leverage

    def get_symbol(self) -> str:
        return self.symbol

    def is_cross_leverage(self) -> bool:
        return self.leverage == 0

    def get_leverage(self) -> int:
        return self.leverage


class OrderPlaceable(ABC):
    """
    Base type for anything order-like which can be submitted to the exchange.
    """
    pass


class Order(OrderPlaceable):
    """
    Base type for standard order types (limit and market).
    """
    @abstractmethod
    def __init__(self, qty: int, contract: Contract, side: Side):
        self.qty = qty
        self.contract = contract
        self.side = side

    def get_qty(self) -> int:
        """
        :return: the number of contracts to trade
        """
        return self.qty

    def get_contract(self) -> Contract:
        return self.contract

    def get_side(self) -> Side:
        return self.side


class ConditionalOrder(OrderPlaceable):
    """
    An order that fires when a particular price condition is met.
    """
    def __init__(self, trigger: Trigger, trigger_price: float, order: Order, close_on_trigger: bool = False):
        self.trigger = trigger
        self.trigger_price = trigger_price
        self.order = order
        self.close_on_trigger = close_on_trigger

    def get_trigger(self) -> Trigger:
        return self.trigger

    def get_trigger_price(self) -> float:
        return self.trigger_price

    def is_close_on_trigger(self) -> bool:
        return self.close_on_trigger

    def get_order(self) -> Order:
        return self.order


class LimitOrder(Order):
    """
    An order with a maximum (buy) or minimum (sell) price to trade.
    """
    def __init__(self, price: float, qty: int, contract: Contract, side: Side,
                 time_in_force: TimeInForce = TimeInForce.GTC,
                 post_only: bool = False, reduce_only: bool = False):
        super().__init__(qty, contract, side)
        self.price = price
        self.time_in_force = time_in_force
        self.post_only = post_only
        self.reduce_only = reduce_only

    def get_price(self) -> float:
        return self.price

    def get_time_in_force(self) -> TimeInForce:
        return self.time_in_force

    def is_post_only(self) -> bool:
        return self.post_only

    def is_reduce_only(self) -> bool:
        return self.reduce_only


class MarketOrder(Order):
    """
    An order that executes at the prevailing market price.
    """
    def __init__(self, qty: int, contract: Contract, side: Side):
        super().__init__(qty, contract, side)


class OrderHandle(ABC):
    """
    An opaque reference to an order that has been placed on the exchange.
    """
    @abstractmethod
    def cancel(self):
        """
        Cancels the referenced order.
        :return: None
        """
        pass


class OrderFactory:
    """
    Helper factory for creating instances of different order types.
    """

    @staticmethod
    def create_market_order(side: Side, qty: int, contract: Contract) -> MarketOrder:
        return MarketOrder(qty, contract, side)

    @staticmethod
    def create_limit_order(side: Side, qty: int, price: float, contract: Contract,
                           time_in_force: TimeInForce = TimeInForce.GTC,
                           post_only: bool = False, reduce_only: bool = False) -> LimitOrder:
        return LimitOrder(price, qty, contract, side, time_in_force, post_only, reduce_only)


class OrderPlacer(ABC):
    """
    Abstraction for the trading connection to the exchange.
    """

    def __init__(self, order_factory: OrderFactory):
        self.order_factory = order_factory

    def get_order_factory(self) -> OrderFactory:
        """"
        :return: the associated order factory object for this OrderPlacer
        """
        return self.order_factory

    @abstractmethod
    def submit(self, order: OrderPlaceable) -> OrderHandle:
        """
        Places the given OrderPlaceable on the exchange
        :param order: order details
        :return: a handle to control the order
        """
        pass

    @abstractmethod
    def cancel(self, handle: OrderHandle):
        """
        Cancels the referenced order.
        :param handle: pointer to the order
        :return: None
        """
        pass

    @abstractmethod
    def cancel_all(self, symbol: str):
        """
        Cancels all open orders for a symbol
        :return: None
        """
        pass
