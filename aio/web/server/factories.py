import os
import json
import ast
import asyncio

from zope.dottedname.resolve import resolve
import aiohttp_jinja2
import jinja2

from aio.core.exceptions import MissingConfiguration, BadConfiguration
import aio.app

import logging
log = logging.getLogger("aio.web")


class FileSystemLoader(jinja2.FileSystemLoader):
    pass


def get_template_dirs(conf):
    template_dirs = ''
    try:
        template_dirs = conf['template_dirs']
    except KeyError:
        try:
            template_dirs = aio.app.config["aio/web"]["template_dirs"]
        except (KeyError, TypeError):
            pass
    except TypeError:
        pass
    if template_dirs:
        return [
            x.strip() for x in
            template_dirs.split("\n") if x.strip()]
    return []


def get_factory_modules(conf):
    factory_modules = ''
    try:
        factory_modules = conf['modules']
    except KeyError:
        try:
            factory_modules = aio.app.config["aio/web"]["modules"]
        except KeyError:
            try:
                factory_modules = aio.app.config["aio"]["modules"]
            except KeyError:
                pass
        except TypeError:
            pass
    except TypeError:
        pass
    return [
        x.strip() for x in
        factory_modules.split("\n") if x.strip()]


@asyncio.coroutine
def filters_factory(web_app, conf):
    filter_conf = conf.get("filters")
    if not filter_conf:
        try:
            filter_conf = aio.app.config["aio/web"]["filters"]
        except (TypeError, KeyError):
            return

    filters = [
        x.strip() for x in
        filter_conf.split("\n")
        if x]

    env = aiohttp_jinja2.get_env(web_app)
    for filt in filters:
        try:
            name, handler = [x for x in filt.split(" ") if x]
        except ValueError:
            BadConfiguration("Bad filter definition: %s" % filt)
        try:
            env.filters[name] = resolve(handler)
        except ImportError:
            raise BadConfiguration("Cannot import filter %s (%s)" % (
                name, handler))


@asyncio.coroutine
def static_factory(web_app, conf):
    web_app['static'] = []

    if "static_url" in conf and "static_dir" in conf:
        log.debug("Setting up static folders for: %s" % web_app['name'])
        static_dir = conf['static_url']
        static_url = os.path.abspath(conf['static_dir'])
        web_app.router.add_static(
            static_dir, static_url)


@asyncio.coroutine
def templates_factory(web_app, conf):
    templates = []
    template_modules = get_factory_modules(conf)
    template_dirs = get_template_dirs(conf)

    if template_modules:
        log.debug("Setting up templates for: %s" % web_app['name'])
        for module in template_modules:
            templates.append(
                os.path.join(
                    resolve(module).__path__[0], "templates"))

    if template_dirs:
        for template_dir in template_dirs:
            templates.append(os.path.abspath(template_dir))

    if templates:
        aiohttp_jinja2.setup(web_app, loader=FileSystemLoader(templates))
    else:
        aiohttp_jinja2.setup(web_app)

    yield from filters_factory(web_app, conf)


@asyncio.coroutine
def routes_factory(web_app, conf):
    log.debug("Setting up routes for: %s" % web_app['name'])
    if not aio.app.config:
        return
    route_definitions = "web/%s/" % web_app['name']
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
        web_app.router.add_route(method, match, handler, name=name)


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
