import os
import asyncio
import functools
import mimetypes

from zope.dottedname.resolve import resolve
import aiohttp
import aiohttp_jinja2

import aio.app
import aio.http.server
import aio.web.server
from aio.core.exceptions import MissingConfiguration

import logging
log = logging.getLogger("aio.web")
apps = {}

APP_KEY = "aio_web_environment"


@asyncio.coroutine
def protocol(name):
    if not aio.app.config:
        raise MissingConfiguration("No system configuration!")
    
    http_protocol = yield from aio.http.server.protocol(name)
    webapp = http_protocol._app
    aio.web.server.apps[name] = webapp
    try:
        conf = aio.app.config["web/%s" % name]
    except KeyError:
        conf = {}

    if "aio/web" in aio.app.config:
        web_config = aio.app.config["aio/web"]
    else:
        web_config = None

    if conf.get("factory_types", None):
        factory_types = conf['factory_types'].split("\n")
    elif web_config and web_config.get("factory_types", None):
        factory_types = web_config['factory_types'].split("\n")
    else:
        factory_types = []

    factories = []
    for factory_name in factory_types:
        factory_key = "%s_factory" % factory_name
        if conf.get(factory_key):
            factory = resolve(conf[factory_key])
        elif aio.app.config['aio/web'].get(factory_key):
            factory = resolve(aio.app.config['aio/web'][factory_key])
        if factory:
            factories.append(factory(webapp, conf))

    yield from asyncio.gather(*factories)
    return http_protocol


@asyncio.coroutine
def factory(name, proto, address, port):
    return (
        yield from aio.http.server.factory(
            name, proto or protocol, address, port))


def clear():
    aio.web.server.apps = {}
    aio.app.clear()


def route(*la, **kwa):
    """
    - optionally called with a template
    - calls handler with configuration object
    - handler can return a response object or context
    - if response object, then response object is returned
    - else if there is a template, then template is rendered with the context
    - else raises exception


    """
    app_key = kwa.get("app_key", aiohttp_jinja2.APP_KEY)
    encoding = kwa.get("encoding", 'utf-8')
    status = kwa.get("status", 200)

    if len(la) == 1 and not callable(la[0]):
        template_name = la[0]
    else:
        template_name = None

    def wrapper(func):

        @asyncio.coroutine
        @functools.wraps(func)
        def wrapped(*la, **kwa):
            request = la[0]
            http_log = logging.getLogger("aio.http.request")
            http_log.info(request)
            route_name = request.match_info.route.name
            try:
                handler_config = aio.app.config[route_name]
            except KeyError:
                handler_config = None

            if asyncio.iscoroutinefunction(func):
                coro = func
            else:
                coro = asyncio.coroutine(func)

            try:
                context = yield from coro(
                    *la, config=handler_config)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error("Error calling route handler: %s" % e)
                raise e

            if isinstance(context, aiohttp.web.StreamResponse):
                return context

            try:
                response = aiohttp_jinja2.render_template(
                    template_name, request, context,
                    app_key=app_key, encoding=encoding)
                response.set_status(status)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error("Error calling route (%s): %s" % (
                    template_name, e))
                raise e
            return response
        return wrapped
    if len(la) == 1 and callable(la[0]):
        return wrapper(la[0])
    return wrapper


def template(*la, **kwa):
    """
    calls handler
    - hander can return a response object or context
    - if context, context is returned
    - else the the template is rendered
    """
    app_key = kwa.get("app_key", aiohttp_jinja2.APP_KEY)
    encoding = kwa.get("encoding", 'utf-8')
    status = kwa.get("status", 200)

    if len(la) == 1 and not callable(la[0]):
        template_name = la[0]
    else:
        template_name = None

    def wrapper(func):

        @asyncio.coroutine
        @functools.wraps(func)
        def wrapped(*la, **kwa):
            request = la[0]

            if asyncio.iscoroutinefunction(func):
                coro = func
            else:
                coro = asyncio.coroutine(func)

            try:
                context = yield from coro(*la)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error("Error calling template handler: %s" % e)
                raise e
            try:
                response = aiohttp_jinja2.render_template(
                    template_name, request, context,
                    app_key=app_key,
                    encoding=encoding)
                response.set_status(status)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error("Error calling template (%s): %s" % (
                    template_name, e))
                raise e
            return response
        return wrapped
    if len(la) == 1 and callable(la[0]):
        return wrapper(la[0])
    return wrapper


def fragment(*la, **kwa):
    app_key = kwa.get("app_key", aiohttp_jinja2.APP_KEY)

    if len(la) == 1 and not callable(la[0]):
        template_name = la[0]
    else:
        template_name = None

    def wrapper(func):

        @asyncio.coroutine
        @functools.wraps(func)
        def wrapped(*la, **kwa):
            request = la[0]

            if asyncio.iscoroutinefunction(func):
                coro = func
            else:
                coro = asyncio.coroutine(func)

            try:
                context = yield from coro(*la)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error("Error calling fragment handler: %s" % e)
                raise e

            if isinstance(context, str):
                return context

            if not template_name:
                error_message = (
                    "Fragment handler (%s) should provide a template" % func
                    + " or return a string")
                log.error(error_message)
                raise Exception(error_message)

            try:
                response = aiohttp_jinja2.render_string(
                    template_name, request, context,
                    app_key=app_key)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error("Error calling fragment (%s): %s" % (
                    template_name, e))
                raise e
            return response
        return wrapped
    if len(la) == 1 and callable(la[0]):
        return wrapper(la[0])
    return wrapper


def filestream(request, filepath):
    resp = aiohttp.web.StreamResponse()
    limit = aiohttp.web_urldispatcher.StaticRoute.limit
    ct, encoding = mimetypes.guess_type(
        os.path.basename(filepath))
    if not ct:
        ct = 'application/octet-stream'
    resp.content_type = ct
    if encoding:
        resp.headers['content-encoding'] = encoding

    file_size = os.stat(filepath).st_size
    single_chunk = file_size < limit

    if single_chunk:
        resp.content_length = file_size
    resp.start(request)

    with open(filepath, 'rb') as f:
        chunk = f.read(limit)
        if single_chunk:
            resp.write(chunk)
        else:
            while chunk:
                resp.write(chunk)
                chunk = f.read(limit)
    return resp
