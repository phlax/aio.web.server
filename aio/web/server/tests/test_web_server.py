import asyncio

from aio.testing import aiofuturetest
from aio.web.server.testing import AioWebAppTestCase
from aio.app.runner import runner

CONFIG = """
[server/test]
factory = aio.web.server.factory
port = 7070

[web/test/route]
match = /
route = aio.web.server.tests.handle_hello_web_world
"""


class WebServerTestCase(AioWebAppTestCase):

    @aiofuturetest(sleep=1)
    def test_web_server(self):
        yield from runner(
            ['run'], config_string=CONFIG)

        @asyncio.coroutine
        def _test():
            pass

        return _test

    @aiofuturetest(sleep=2)
    def test_web_root(self):
        yield from runner(
            ['run'], config_string=CONFIG)
