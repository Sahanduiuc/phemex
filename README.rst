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



Installation
------------

.. code-block:: bash

    $ pip install phemex
