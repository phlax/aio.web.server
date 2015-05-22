import os
import json
import ast
import asyncio

from zope.dottedname.resolve import resolve
import aiohttp_jinja2
import jinja2

from aio.core.exceptions import MissingConfiguration
import aio.app

import logging
log = logging.getLogger("aio.web")


class FileSystemLoader(jinja2.FileSystemLoader):
    pass


@asyncio.coroutine
def filters_factory(webapp, conf):
    if conf.get("filters"):
        env = aiohttp_jinja2.get_env(webapp)
        for filt in conf['filters'].split("\n"):
            name, handler = [x for x in filt.split(" ") if x]
            env.filters[name] = resolve(handler)


@asyncio.coroutine
def static_factory(webapp, conf):
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
def templates_factory(webapp, conf):
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
def routes_factory(webapp, conf):
    log.debug("Setting up routes for: %s" % webapp['name'])
    route_definitions = "web/%s/" % webapp['name']
    route_sections = [
        (x, aio.app.config[x]) for x in aio.app.config.sections()
        if x.startswith(route_definitions)]
    for name, route_config in route_sections:
        try:
            match = route_config['match']
        except KeyError:
            raise MissingConfiguration(
                'Section %s should specify "match" for route' % (
                    route_definitions))
        if match.startswith('r"') or match.startswith("r'"):
            match = ast.literal_eval(match)
        method = route_config.get("method", "GET")

        try:
            handler = resolve(route_config['route'])
        except KeyError:
            raise MissingConfiguration(
                'Section %s should specify "route" for route' % (
                    route_definitions))

        log.debug('adding route (%s): %s %s %s' % (
            name, method, match, handler))
        webapp.router.add_route(method, match, handler, name=name)


@asyncio.coroutine
def sockets_factory(webapp, conf):
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
