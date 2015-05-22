aio.web.server
==============

Web server for the aio_ asyncio framework

.. _aio: https://github.com/phlax/aio



Build status
------------

.. image:: https://travis-ci.org/phlax/aio.web.server.svg?branch=master
	       :target: https://travis-ci.org/phlax/aio.web.server


Installation
------------
Install with:

.. code:: bash

	  pip install aio.web.server


Configuration
-------------

Example configuration for a hello world web page

.. code:: ini

	  [server/test]
	  factory = aio.web.server.factory
	  port = 8080

	  [web/test/page]
	  match = /
	  route = my.example.handler

And the corresponding route handler

.. code:: python

	  import asyncio
	  import aiohttp

	  @asyncio.coroutine
	  def handler(request):
	      return aiohttp.web.Response(body=b"Hello, web world")


Running
-------

Run with the aio command

.. code:: bash

	  aio run

