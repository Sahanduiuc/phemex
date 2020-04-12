from phemex import PhemexConnection, AuthCredentials
from phemex.order import Side, Contract, ConditionalOrder, Trigger, Condition

api_key = 'xxxxx'
secret_key = '*****'
credentials = AuthCredentials(api_key=api_key, secret_key=secret_key)
conn = PhemexConnection(credentials)

# set up order helper classes
order_placer = conn.get_order_placer()
order_factory = order_placer.get_order_factory()

# create a limit order
limit = order_factory.create_limit_order(Side.SELL, 1, 10000.0, Contract('BTCUSD'))

# create a market order for BTCUSD, "cross" (no leverage), buy / long
order = order_factory.create_market_order(Side.SELL, 1, Contract('BTCUSD'))

# build up a conditional that places the given market order
# when last trade price touches 10000
conditional = ConditionalOrder(Condition.IF_TOUCHED, Trigger.LAST_PRICE, 10000.0, order)

# place the orders
limit_hnd = order_placer.submit(limit)
cond_hnd = order_placer.submit(conditional)

# cancel them
limit_hnd.cancel()
cond_hnd.cancel()
