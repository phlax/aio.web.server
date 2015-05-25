import aiohttp

import aio.web


@aio.web.server.route
def hello_world_route(route):
    return aiohttp.web.Response(body=b"Hello, web world")
