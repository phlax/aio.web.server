import os
import json
import asyncio
import ast
import functools
import mimetypes

from zope.dottedname.resolve import resolve
import aiohttp
import aiohttp_jinja2
import jinja2

import aio.app

import logging
log = logging.getLogger("aio.web")
apps = {}

APP_KEY = "aio_web_environment"


class FileSystemLoader(jinja2.FileSystemLoader):
    pass


@asyncio.coroutine
def setup_filters(webapp, conf):
    if conf.get("filters"):
        env = aiohttp_jinja2.get_env(webapp)
        for filt in conf['filters'].split("\n"):
            name, handler = [x for x in filt.split(" ") if x]
            env.filters[name] = resolve(handler)


@asyncio.coroutine
def setup_static(webapp, conf):
    webapp['static'] = []

    if "static_url" in conf and "static_dir" in conf:
        log.debug("Setting up static folders for: %s" % webapp['name'])
        webapp.router.add_static(
            conf['static_url'],
            os.path.abspath(conf['static_dir']))

        for module in aio.app.modules:
            path = os.path.join(
                module.__path__[0], "static")
            if os.path.exists(path):
                webapp['static'].append((module.__name__, path))


@asyncio.coroutine
def setup_templates(webapp, conf):
    templates = []

    try:
        template_modules = aio.app.config['web/%s']['modules']
    except KeyError:
        try:
            template_modules = aio.app.config["aio/web"]["modules"]
        except KeyError:
            try:
                template_modules = aio.app.config["aio"]["modules"]
            except KeyError:
                template_modules = ''

    if not template_modules:
        return

    log.debug("Setting up templates for: %s" % webapp['name'])

    for module in [x.strip() for x in template_modules.split("\n")]:
        templates.append(
            os.path.join(
                resolve(module).__path__[0], "templates"))
    aiohttp_jinja2.setup(webapp, loader=FileSystemLoader(templates))


@asyncio.coroutine
def setup_routes(webapp, conf):
    log.debug("Setting up routes for: %s" % webapp['name'])
    route_definitions = "web/%s/" % webapp['name']
    route_sections = [
        (x, aio.app.config[x]) for x in aio.app.config.sections()
        if x.startswith(route_definitions)]
    for name, route_config in route_sections:
        match = route_config['match']
        if match.startswith('r"') or match.startswith("r'"):
            match = ast.literal_eval(match)
        method = route_config.get("method", "GET")
        handler = resolve(route_config['route'])

        log.debug('adding route (%s): %s %s %s' % (
            name, method, match, handler))
        webapp.router.add_route(method, match, handler, name=name)


@asyncio.coroutine
def setup_sockets(webapp, conf):
    if not conf.get('sockets'):
        return
    log.debug("Setting up websockets for: %s" % webapp['name'])
    webapp['sockets'] = []

    @asyncio.coroutine
    def cb_sockets_emit(signal, msg):
        yield from aio.app.signals.emit('sockets-emitted', ['emit', msg])
        for socket in webapp['sockets']:
            socket.send_str(json.dumps(msg))

    @asyncio.coroutine
    def cb_sockets_info(signal, msg):
        yield from aio.app.signals.emit('sockets-emitted', ['info', msg])
        for socket in webapp['sockets']:
            socket.send_str(
                json.dumps({'info': msg}))

    @asyncio.coroutine
    def cb_sockets_error(signal, msg):
        yield from aio.app.signals.emit('sockets-emitted', ['error', msg])
        for socket in webapp['sockets']:
            socket.send_str(
                json.dumps({'error': msg}))

    aio.app.signals.listen('sockets-info', cb_sockets_info)
    aio.app.signals.listen('sockets-error', cb_sockets_error)
    aio.app.signals.listen('sockets-emit', cb_sockets_emit)


@asyncio.coroutine
def protocol(name):
    import aio.http.server
    http_protocol = yield from aio.http.server.protocol(name)
    webapp = http_protocol._app
    import aio.web.server
    aio.web.server.apps[name] = webapp
    try:
        conf = aio.app.config["web/%s" % name]
    except KeyError:
        conf = {}
    yield from setup_templates(webapp, conf)
    yield from setup_filters(webapp, conf)
    yield from setup_routes(webapp, conf)
    yield from setup_static(webapp, conf)
    yield from setup_sockets(webapp, conf)
    return http_protocol


@asyncio.coroutine
def factory(name, proto, address, port):
    import aio.http.server    
    return (
        yield from aio.http.server.factory(
            name, proto or protocol, address, port))


def clear():
    import aio.web.server
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

from aio.web.server import fragments
fragments


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
