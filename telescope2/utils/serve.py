from pathlib import Path

from aiohttp import web

routes = web.RouteTableDef()


@routes.get(r'/static/{path:.+}')
async def serve(req: web.Request):
    path = Path(req.match_info['path'])
    root: Path = req.app['STATIC_ROOT']
    path = root / path
    if not path.exists():
        return web.HTTPNotFound()
    if not path.is_file():
        return web.HTTPNotFound()
    return web.FileResponse(path.resolve())


def create_app(root) -> web.Application:
    app = web.Application()
    app['STATIC_ROOT'] = root
    app.add_routes(routes)
    return app


def run(root, port):
    web.run_app(create_app(root), port=port)
