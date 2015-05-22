aio.web.server usage
-------------


Configuration
-------------

Let's create a config defining a factory method and using the aio.web.server.protocol for the protocol

In the following configuration example a server named "example-1" is set up.

Any sections that start with "web/example-1/" will be treated as route definitions.

The route definition should provide a "match" and a "handler" at a minimum.

The route is given a name derived from the section name. In this case "homepage"

  >>> web_server_config = """
  ... [aio]
  ... log_level: ERROR
  ... 
  ... [server/example]
  ... factory = aio.web.server.server
  ... port = 7070
  ... 
  ... [web/example/homepage]
  ... match = /
  ... handler = aio.web.server.tests._example_handler
  ... """  

  >>> import asyncio
  >>> import aiohttp
  >>> import aio.web.server.tests
  >>> from aio.app.runner import runner    
  >>> from aio.testing import aiofuturetest

  >>> def handler(request):
  ...     return aiohttp.web.Response(body=b"Hello, web world")    

  >>> aio.web.server.tests._example_handler = asyncio.coroutine(handler)
  
  >>> def run_web_server(config, request_page="http://localhost:7070"):
  ...     yield from runner(['run'], config_string=config)
  ... 
  ...     @asyncio.coroutine
  ...     def call_web_server():
  ...         result = yield from (
  ...             yield from aiohttp.request(
  ...                "GET", request_page)).read()
  ... 
  ...         print(result.decode())
  ... 
  ...     return call_web_server

  >>> aiofuturetest(run_web_server, sleep=1)(web_server_config)  
  Hello, web world

  
Accessing web apps
------------------

You can access a webapp by name

  >>> import aio.web.server
  >>> aio.web.server.apps['example']
  <Application>

  >>> aio.web.server.apps['example']['name']
  'example'

Let's clear the web apps, this will also call aio.app.clear()

  >>> aio.web.server.clear()
  >>> aio.web.server.apps
  {}

  >>> print(aio.app.config, aio.app.signals)
  None None

  
Static directory
----------------

The "web/" section takes a static_url and a static_dir option for hosting static files

  >>> config_static = """
  ... [aio]
  ... log_level: ERROR
  ... 
  ... [server/test]
  ... factory: aio.web.server.server
  ... port: 7070
  ... 
  ... [web/test]
  ... static_url: /static
  ... static_dir: %s
  ... """

  >>> import os
  >>> import tempfile
  >>> with tempfile.TemporaryDirectory() as tmp:
  ...     with open(os.path.join(tmp, "test.css"), 'w') as cssfile:
  ...         res = cssfile.write("body {}")
  ... 
  ...     aiofuturetest(run_web_server, sleep=1)(
  ...         config_static % tmp, "http://localhost:7070/static/test.css")  
  body {}

And clear up...

  >>> aio.web.server.clear()
  

Routes, templates and fragments
-------------------------------

aio.web.server uses jinja2 templates under the hood

On setup aio searches the paths of modules listed in the aio:modules option for folders named "templates" and loads any templates it finds from there

  >>> config_template = """
  ... [aio]
  ... modules = aio.web.server.tests
  ... log_level: ERROR
  ... 
  ... [server/example-2]
  ... factory: aio.web.server.server
  ... port: 7070
  ... 
  ... [web/example-2/homepage]
  ... match = /
  ... handler = aio.web.server.tests._example_route_handler
  ... """

By decorating the route_handler function with @aio.web.server.route, the function is called with the request and the configuration for the route that is being handled
 
  >>> def route_handler(request, config):
  ...     return {
  ...         'message': 'Hello, world'}

  >>> aio.web.server.tests._example_route_handler = (
  ...     aio.web.server.route('test_template.html')(route_handler))
  
  >>> aiofuturetest(run_web_server, sleep=1)(config_template)
  <html>
    <body>
      Hello, world
    </body>
  </html>

  >>> aio.web.server.clear()

A route handler can defer to other templates, for example according to the path. The @aio.web.server.route decorator does not require a template

  >>> example_config_2 = """
  ... [aio]
  ... modules = aio.web.server.tests
  ... log_level: ERROR
  ... 
  ... [server/example-3]
  ... factory: aio.web.server.server
  ... port: 7070
  ... 
  ... [web/example-3/homepage]
  ... match = /
  ... handler = aio.web.server.tests._example_route_handler_2
  ... """


  >>> def template_handler(request):
  ...     return {'message': "Hello, world in a template"}
  
  >>> def route_handler_2(request, config):
  ...     import pdb; pdb.set_trace()
  
  ...     return (yield from aio.web.server.template('test_template.html')(template_handler, request))

  >>> aio.web.server.tests._example_route_handler_2 = aio.web.server.route(route_handler_2)
  
  >>> aiofuturetest(run_web_server, sleep=1)(example_config_2)

  
	
We can get the associated templates for the web app

  >>> webapp = aio.web.server.apps['example-2']

  >>> import aiohttp_jinja2
  >>> aiohttp_jinja2.get_env(webapp).list_templates()
  ['test_template.html']

  >>> aio.web.server.clear()
