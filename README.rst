Phemex: A Python API
=====================

.. image:: https://img.shields.io/pypi/v/phemex.svg
    :target: https://pypi.org/project/phemex/

.. image:: https://img.shields.io/pypi/l/phemex.svg
    :target: https://pypi.org/project/phemex/

.. image:: https://img.shields.io/pypi/pyversions/phemex.svg
    :target: https://pypi.org/project/phemex/

Features
--------
- Initial, limited support of Phemex REST API
    - Public API:

    .. code-block:: python

        >>> from cloudwall.phemex import PhemexConnection
        >>> conn = PhemexConnection()
        >>> products = conn.get_products()

    - Authenticated connections:

    .. code-block:: python

        >>> from cloudwall.phemex import PhemexConnection, AuthCredentials
        >>> credentials = AuthCredentials(api_key, secret_key)
        >>> conn = PhemexConnection()
        >>> products = conn.get_products()

    - Placing orders:

    .. code-block:: python

        conn = PhemexConnection(credentials)

        # set up order helper classes
        order_placer = conn.get_order_placer()
        order_factory = order_placer.get_order_factory()

        # create a limit order
        limit = order_factory.create_limit_order(Side.SELL, 1, 10000.0, Contract('BTCUSD'))

        # create a market order for BTCUSD, "cross" (no leverage), sell / short
        order = order_factory.create_market_order(Side.SELL, 1, Contract('BTCUSD'))

        # build up a conditional that places the given market short sell order
        # when last trade price touches 8800
        conditional = ConditionalOrder(Condition.IF_TOUCHED, Trigger.LAST_PRICE, 10000.0, order)

        # place the orders
        limit_hnd = order_placer.submit(limit)
        cond_hnd = order_placer.submit(conditional)

        # cancel them
        limit_hnd.cancel()
        cond_hnd.cancel()


Installation
------------

.. code-block:: bash

    $ pip install phemex
