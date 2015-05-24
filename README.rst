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

Requires python >= 3.4

Install with:

.. code:: bash

	  pip install aio.web.server

	  
Quick start - Hello world web server
------------------------------------

Create a web server that says hello

Save the following into a file "hello.conf"

.. code:: ini

	  [aio]
	  modules = aio.web.server

	  [server/my_server]
	  factory = aio.web.server.factory
	  port = 8080

	  [web/my_server/my_route]
	  match = /
	  route = my_example.handler

	  
And save the following into a file named my_example.py
	  
.. code:: python

	  import aiohttp
	  import aio.web.server

	  @aio.web.server.route
	  def handler(request, config):
	      return aiohttp.web.Response(body=b"Hello, web world")


Run with the aio run command

.. code:: bash

	  aio run -c hello.conf

