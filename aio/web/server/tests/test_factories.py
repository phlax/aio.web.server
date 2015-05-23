import os
import asyncio
import tempfile
from configparser import ConfigParser

import aiohttp
import aiohttp_jinja2

import aio.testing
from aio.web.server.testing import AioWebAppTestCase
from aio.web.server import factories
from aio.core.exceptions import BadConfiguration
import aio.web.server.tests.test_factories


TEST_DIR = os.path.basename(
    os.path.abspath(__file__))


class WebFactoryTestCase(AioWebAppTestCase):

    @asyncio.coroutine
    def _get_web_app(self):
        loop = asyncio.get_event_loop()
        web_app = aiohttp.web.Application(loop=loop)
        web_app['name'] = "TEST"
        return web_app


def example_filter():
    pass


@asyncio.coroutine
def test_route():
    pass


class WebSetupFactoryTestCase(WebFactoryTestCase):

    @asyncio.coroutine
    def _get_web_app(self):
        web_app = yield from WebFactoryTestCase._get_web_app(self)

        # setup jinja
        yield from factories.templates_factory(web_app, {})
        return web_app


class WebRoutesFactoryTestCase(WebSetupFactoryTestCase):

    @aio.testing.run_until_complete
    def test_routes_factory_no_config(self):
        web_app = yield from self._get_web_app()
        yield from factories.routes_factory(
            web_app,
            {})

    @aio.testing.run_until_complete
    def test_routes_factory(self):
        config = ConfigParser()
        config.read_dict(
            {'web/TEST/route': {
                'match': '/',
                'route': "aio.web.server.tests.test_factories.test_route"}})
        aio.app.config = config
        web_app = yield from self._get_web_app()
        yield from factories.routes_factory(
            web_app,
            {})
        self.assertEqual(
            web_app.router['web/TEST/route'].url(), "/")


class WebStaticFactoryTestCase(WebSetupFactoryTestCase):

    @aio.testing.run_until_complete
    def test_static_factory_no_config(self):
        web_app = yield from self._get_web_app()
        yield from factories.static_factory(
            web_app,
            {})
        self.assertEqual(
            web_app.router._urls, [])

    @aio.testing.run_until_complete
    def test_static_factory(self):
        """
        [web/TEST]
        static_dir = TMP
        static_url = /test
        """
        with tempfile.TemporaryDirectory() as tmp:
            web_app = yield from self._get_web_app()
            yield from factories.static_factory(
                web_app,
                dict(
                    static_dir=tmp,
                    static_url="/test_static"))
            urls = web_app.router._urls
            self.assertEqual(
                urls[0].url(filename=""), "/test_static/")
            self.assertEqual(
                urls[0]._directory, tmp)


class WebTemplatesFactoryTestCase(WebFactoryTestCase):

    @aio.testing.run_until_complete
    def test_templates_factory_no_config(self):
        """
        [web/TEST]
        """
        web_app = yield from self._get_web_app()
        yield from factories.templates_factory(
            web_app,
            {})
        env = aiohttp_jinja2.get_env(web_app)
        with self.assertRaises(AttributeError):
            env.list_templates()

    @aio.testing.run_until_complete
    def test_templates_factory_web_conf(self):
        """
        [web/TEST]
        modules = aio.web.server.tests
        """
        web_app = yield from self._get_web_app()
        yield from factories.templates_factory(
            web_app,
            {'modules': 'aio.web.server.tests'})
        env = aiohttp_jinja2.get_env(web_app)
        self.assertEqual(
            [x for x in env.list_templates(extensions=["html"])],
            ['fragments/test_fragment.html', 'test_template.html'])

    @aio.testing.run_until_complete
    def test_templates_factory_web_app_conf(self):
        """
        [aio/web]
        modules = aio.web.server.tests
        """
        aio.app.config = {
            'aio/web': {'modules': 'aio.web.server.tests'}}
        web_app = yield from self._get_web_app()
        yield from factories.templates_factory(
            web_app,
            {})
        env = aiohttp_jinja2.get_env(web_app)
        self.assertEqual(
            [x for x in env.list_templates(extensions=["html"])],
            ['fragments/test_fragment.html', 'test_template.html'])

    @aio.testing.run_until_complete
    def test_templates_factory_aio_conf(self):
        """
        [aio]
        modules = aio.web.server.tests
        """
        aio.app.config = {
            'aio/web': {'modules': 'aio.web.server.tests'}}
        web_app = yield from self._get_web_app()
        yield from factories.templates_factory(
            web_app,
            {})
        env = aiohttp_jinja2.get_env(web_app)
        self.assertEqual(
            [x for x in env.list_templates(extensions=["html"])],
            ['fragments/test_fragment.html', 'test_template.html'])

    @aio.testing.run_until_complete
    def test_templates_factory_multiple_modules(self):
        """
        [web/TEST]
        modules = aio.web.server.tests
        """
        web_app = yield from self._get_web_app()
        yield from factories.templates_factory(
            web_app,
            {'modules': 'aio.web.server.tests\naio.web.server'})
        env = aiohttp_jinja2.get_env(web_app)
        templ_list = [
            x for x in env.list_templates(extensions=["html"])]
        self.assertEqual(
            sorted(templ_list),
            ['fragments/test_fragment.html', 'test_template.html'])


class WebFiltersFactoryTestCase(WebSetupFactoryTestCase):

    @aio.testing.run_until_complete
    def test_filters_factory_no_config(self):
        yield from factories.filters_factory(
            (yield from self._get_web_app()),
            {})

    @aio.testing.run_until_complete
    def test_filters_factory(self):
        web_app = yield from self._get_web_app()
        yield from factories.filters_factory(
            web_app,
            {'filters': (
                "my_filter "
                + "aio.web.server.tests.test_factories.example_filter")})
        env = aiohttp_jinja2.get_env(web_app)
        self.assertEqual(
            env.filters['my_filter'],
            aio.web.server.tests.test_factories.example_filter)

    @aio.testing.run_until_complete
    def test_filters_factory_bad_handler(self):
        web_app = yield from self._get_web_app()
        with self.assertRaises(BadConfiguration):
            yield from factories.filters_factory(
                web_app,
                {'filters': (
                    "my_filter "
                    + "aio.web.server.tests.test_factories._BAD_filter")})
