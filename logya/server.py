# -*- coding: utf-8 -*-
import http.server
import socketserver

from pathlib import Path
from shutil import copyfile
from urllib.parse import unquote, urlparse

from logya.core import Logya
from logya.content import add_collections, read, read_all, write_collection
from logya.util import load_settings

# Deprecated imports
from logya.writer import DocWriter


settings = load_settings()
site_index = read_all(settings)

L = Logya()
L.init_env()
L.build_index()
L.template.vars['debug'] = True


class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler based class to return resources."""

    def __init__(self, *args):
        super(HTTPRequestHandler, self).__init__(*args, directory=settings['paths']['public'].as_posix())

    def do_GET(self):
        update_resource(self.path)
        super(HTTPRequestHandler, self).do_GET()


def update_resource(path):
    """Update resource corresponding to given url.

    Resources that exist in the `static` directory are updated if they are newer than the destination file.
    For other HTML resources the whole `site_index` is updated and the destination is newly written."""

    # Use only the actual path and ignore possible query params (see issue #3).
    path = unquote(urlparse(path).path)
    path_rel = path.lstrip('/')

    # If a static file is requested update it and return.
    src_static = Path(settings['paths']['static'], path_rel)
    if src_static.is_file():
        dst_static = Path(settings['paths']['public'], path_rel)
        dst_static.parent.mkdir(exist_ok=True)
        if not dst_static.exists() or src_static.stat().st_mtime > dst_static.stat().st_mtime:
            print(f'Update static resource: {dst_static}')
            copyfile(src_static, dst_static)
        return True

    # Rebuild index for HTML file requests which are not in index.
    if path.endswith(('/', '.html', '.htm')) and path not in site_index:
        print(f'Rebuild index for request URL: {path}')
        site_index.update(read_all(settings))

    content = site_index[path]
    path_dst = Path(settings['paths']['public'], path_rel, 'index.html')

    # Update content document
    if 'doc' in content:
        content['doc'] = read(content['path'], settings)
        if 'collections' in settings:
            add_collections(content['doc'], site_index, settings['collections'])
        # Always write doc because of possible template changes.
        DocWriter(settings['paths']['public'], L.template).write(content['doc'], L.get_doc_template(content['doc']))
        print(f'Refreshed doc at URL: {path}')
        return

    # Update collection page
    if 'docs' in content:
        write_collection(path_dst, content, L.template, settings)
        print(f'Refreshed collection: {path}')


def serve(args):
    L.template.vars['base_url'] = f'http://{args.host}:{args.port}'
    # Avoid "OSError: [Errno 98] Address already in use"
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), HTTPRequestHandler) as httpd:
        print(f'Serving on {L.template.vars["base_url"]}')
        httpd.serve_forever()