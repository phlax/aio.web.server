import asyncio
from configparser import ConfigParser

import aiohttp.web

from aio.testing import aiofuturetest, aiotest
from aio.web.server.testing import AioWebAppTestCase
import aio.web.server
from aio.core.exceptions import MissingConfiguration

CONFIG = """
[server/test]
factory = aio.web.server.factory
port = 7070

[web/test/route]
match = /
route = aio.web.server.tests.handle_hello_web_world
"""


@asyncio.coroutine
def example_factory(web_app, conf):
    web_app["foo"] = conf["foo"]


class WebServerFactoryTestCase(AioWebAppTestCase):

    @aiotest
    def test_server_factory_no_config(self):
        with self.assertRaises(MissingConfiguration):
            yield from aio.web.server.factory(
                "TEST", None, None, "8080")

    @aiofuturetest
    def test_web_factory_no_port(self):
        aio.app.config = ConfigParser()
        aio.app.config.read_dict({})
        with self.assertRaises(ValueError):
            yield from aio.web.server.factory(
                "TEST", None, None, None)

    @aiofuturetest
    def test_web_factory_empty_config(self):
        aio.app.config = ConfigParser()
        aio.app.config.read_dict({})
        srv = yield from aio.web.server.factory(
            "TEST", None, None, "8080")
        self.assertIsInstance(
            srv, asyncio.base_events.Server)

    @aiofuturetest
    def test_web_factory(self):
        aio.app.config = ConfigParser()
        aio.app.config.read_dict(
            {"aio/web": {
                'factory_types': 'example',
                "example_factory": (
                    "aio.web.server.tests.test_web_server.example_factory")},
             "web/TEST": {
                 "foo": "bar"}})
        srv = yield from aio.web.server.factory(
            "TEST", None, None, "8080")
        self.assertIsInstance(
            srv, asyncio.base_events.Server)
        self.assertEqual(
            aio.web.server.apps['TEST']['foo'],
            "bar")

    @aiofuturetest
    def test_web_factory_custom_protocol(self):
        aio.app.config = ConfigParser()
        aio.app.config.read_dict({})

        @asyncio.coroutine
        def custom_protocol(name):
            loop = asyncio.get_event_loop()
            http_app = aiohttp.web.Application(loop=loop)
            http_app['name'] = name
            http_app['foo'] = 'baz'
            aio.web.server.apps[name] = http_app
            return http_app.make_handler()

        srv = yield from aio.web.server.factory(
            "TEST", custom_protocol, None, "8080")
        self.assertIsInstance(
            srv, asyncio.base_events.Server)
        self.assertEqual(
            aio.web.server.apps['TEST']['foo'],
            "baz")


class WebServerProtocolTestCase(AioWebAppTestCase):

    @aiotest
    def test_web_protocol_no_config(self):
        with self.assertRaises(MissingConfiguration):
            yield from aio.web.server.protocol("TEST")

    @aiotest
    def test_web_protocol_empty_config(self):
        aio.app.config = ConfigParser()
        aio.app.config.read_dict({})
        protocol = yield from aio.web.server.protocol("TEST")
        self.assertIsInstance(
            protocol, aiohttp.web.RequestHandlerFactory)

    @aiotest
    def test_web_protocol_factory(self):
        aio.app.config = ConfigParser()
        aio.app.config.read_dict(
            {"aio/web": {
                'factory_types': 'example',
                "example_factory": (
                    "aio.web.server.tests.test_web_server.example_factory")},
             "web/TEST": {
                 "foo": "bar"}})
        protocol = yield from aio.web.server.protocol("TEST")
        self.assertEqual(
            protocol._app['foo'],
            "bar")
