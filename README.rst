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

Requires python >= 3.4 to work

Install with:

.. code:: bash

	  pip install aio.web.server

Quick start - Hello world web page
----------------------------------

Quickly create a web server that servers a hello world page

The following will create a configuration file "hello.conf"

.. code:: bash

	  aio config -f hello.conf -s aio:modules aio.web.server
	  aio config -f hello.conf -s server/test:factory aio.web.server.factory
	  aio.config -f hello.conf -s web/test/page:match /
	  aio.config -f hello.conf -s web/test/page:route my_example.handler
	  
And save the following into a file named my_example.py
	  
.. code:: python

	  import aiohttp
	  import aio.web.server

	  @aio.web.server.route
	  def handler(request):
	      return aiohttp.web.Response(body=b"Hello, web world")


Run with the aio run command

.. code:: bash

	  aio run -c hello.conf

