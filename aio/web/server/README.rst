aio.web.server usage
--------------------


Configuration
-------------

To set up the web server, we need to:

- add "aio.web.server" to aio:modules initialize the web server
- add a "server/SERVERNAME" section to create the http server
- add a "web/SERVERNAME/ROUTENAME" to create a route

Lets create a basic web server configuration
  
>>> web_server_config = """
... [aio]
... log_level = ERROR
... modules = aio.web.server
... 
... [server/server_name]
... factory = aio.web.server.factory
... port = 7070
... 
... [web/server_name/route_name]
... match = /
... route = aio.web.server.tests._example_handler
... """  

Now lets create a route and make it importable
 
>>> import aiohttp
>>> import aio.web.server

>>> @aio.web.server.route
... def route_handler(route):
...     return aiohttp.web.Response(body=b"Hello, web world")    

>>> import aio.web.server.tests
>>> aio.web.server.tests._example_handler = route_handler


Lets set up a test to run the server and request a web page
  
>>> from aio.app.runner import runner    
>>> import aio.testing

>>> @aio.testing.run_forever(sleep=1)
... def run_web_server(config, request_page="http://localhost:7070"):
...     yield from runner(['run'], config_string=config)
... 
...     def call_web_server():
...         result = yield from (
...             yield from aiohttp.request(
...                "GET", request_page)).read()
...         
...         print(result.decode())
... 
...     return call_web_server

And run the test
  
>>> run_web_server(web_server_config)  
Hello, web world

We can access the aiohttp web app by name

>>> import aio.web.server
>>> web_app = aio.web.server.apps['server_name']
>>> web_app
<Application>

>>> web_app['name']
'server_name'

And we can access the jinja environment for the web app

>>> import aiohttp_jinja2
>>> jinja_env = aiohttp_jinja2.get_env(web_app)
>>> jinja_env
<jinja2.environment.Environment object ...>

We dont have any templates registered yet

>>> jinja_env.list_templates()
[]
  
Let's clear the web apps, this will also call aio.app.clear()

>>> aio.web.server.clear()
>>> aio.web.server.apps
{}

>>> print(aio.app.config, aio.app.signals)
None None

  
Web app modules
---------------

By default template resources are registered for any modules listed in aio:modules

>>> config = """
... [aio]
... modules = aio.web.server
...          aio.web.server.tests
... 
... [server/server_name]
... factory = aio.web.server.factory
... port = 7070  
... """  

Lets create a test to run the server and print the list of installed jinja templates

>>> @aio.testing.run_forever(sleep=1)
... def run_server_print_templates(config_string):
...     yield from runner(['run'], config_string=config_string)
... 
...     def print_templates():
...         web_app = aio.web.server.apps['server_name']
...         print(
...             [x for x in
...              aiohttp_jinja2.get_env(
...                  web_app).list_templates(extensions=["html"])])
...         aio.web.server.clear()
... 
...     return print_templates

The aio.web.server.tests module has 2 html templates
  
>>> run_server_print_templates(config)
['fragments/test_fragment.html', 'test_template.html']
  
We can set the modules for all web apps in the aio/web:modules option

This will override the setting in aio:modules

>>> config = """
... [aio]
... modules = aio.web.server
...       aio.web.server.tests
... 
... [aio/web]
... modules = aio.web.server
... 
... [server/server_name]
... factory = aio.web.server.factory
... port = 7070  
... """  

>>> run_server_print_templates(config)
[]

Or you can set the modules in the web/*SERVER_NAME*:modules option.

This will override the setting in both aio/web:modules and aio:modules
  
>>> config = """
... [aio]
... modules = aio.web.server
...          aio.web.server.tests
... 
... [aio/web]
... modules = aio.web.server
... 
... [web/server_name]
... modules = aio.web.server.tests
... 
... [server/server_name]
... factory = aio.web.server.factory
... port = 7070  
... """  

>>> run_server_print_templates(config)
['fragments/test_fragment.html', 'test_template.html']

Routes
------

>>> config_template = """
... [aio]
... modules = aio.web.server
...        aio.web.server.tests
... log_level: ERROR
... 
... [server/server_name]
... factory: aio.web.server.factory
... port: 7070
... 
... [web/server_name/route_name]
... match = /
... route = aio.web.server.tests._example_route_handler
... """

Route functions must be decorated with aio.server.route, and receive a aio.server.Route object

The route object has a request property and a config property containing the routes configuration

>>> @aio.web.server.route("test_template.html")  
... def route_handler(route):
...     return {
...         'message': 'Hello, world at %s from match(%s) handled by: %s' % (
...             route.request.path, route.config['match'], route.config['route'])}

>>> aio.web.server.tests._example_route_handler = route_handler

>>> run_web_server(config_template)
<html>
  <body>
    Hello, world at / from match(/) handled by: aio.web.server.tests._example_route_handler
  </body>
</html>
  
>>> aio.web.server.clear()


Static directory
----------------

The web/*SERVER_NAME* section takes a static_url and a static_dir option for hosting static files

>>> config_static = """
... [aio]
... log_level: ERROR
... modules = aio.web.server  
... 
... [server/test]
... factory: aio.web.server.factory
... port: 7070
... 
... [web/test]
... static_url: /static
... static_dir: %s
... """

>>> import os
>>> import tempfile

Lets create a temporary directory and add a css file to it
  
>>> with tempfile.TemporaryDirectory() as tmp:
...     with open(os.path.join(tmp, "test.css"), 'w') as cssfile:
...         result = cssfile.write("body {background: black}")
... 
...     run_web_server(
...         config_static % tmp,
...         request_page="http://localhost:7070/static/test.css")  
body {background: black}

>>> aio.web.server.clear()
  

Template filters
----------------

You can configure jinja filters by adding them to the aio/web:filters option


>>> config = """
... [aio]
... log_level: ERROR
... modules = aio.web.server  
... 
... [server/server_name]
... factory: aio.web.server.factory
... port: 7070
... 
... [aio/web]
... filters = example_filter aio.web.server.tests._example_filter
... """

The filter is *not* called in a coroutine

>>> def filter(value, *la):
...     return value

>>> aio.web.server.tests._example_filter = filter

>>> @aio.testing.run_forever(sleep=1)
... def run_server_check_filter(config_string):
...     yield from runner(['run'], config_string=config_string)
... 
...     def check_filter():
...         web_app = aio.web.server.apps['server_name']
...         env = aiohttp_jinja2.get_env(web_app)
... 
...         if "example_filter" in env.filters.keys():
...             print("example_filter is in the jinja environment!")
... 
...     return check_filter


>>> run_server_check_filter(config)
example_filter is in the jinja environment!

>>> aio.web.server.clear()

You can also add filters to the the web/server_name section, this will override the setting in aio/web

>>> config = """
... [aio]
... log_level: ERROR
... modules = aio.web.server  
... 
... [server/server_name]
... factory: aio.web.server.factory
... port: 7070
... 
... [aio/web]
... filters = example_filter aio.web.server.tests._example_filter
... 
... [web/server_name]
... filters = example_filter_2 aio.web.server.tests._example_filter
... """

>>> @aio.testing.run_forever(sleep=1)
... def run_server_check_filter(config_string):
...     yield from runner(['run'], config_string=config_string)
... 
...     def check_filter():
...         web_app = aio.web.server.apps['server_name']
...         env = aiohttp_jinja2.get_env(web_app)
... 
...         if "example_filter" not in env.filters.keys():
...             print("example_filter is not in the jinja environment!")
... 
...         if "example_filter_2" in env.filters.keys():
...             print("example_filter_2 is in the jinja environment!")
... 
...     return check_filter


>>> run_server_check_filter(config)
example_filter is not in the jinja environment!
example_filter_2 is in the jinja environment!


>>> aio.web.server.clear()
