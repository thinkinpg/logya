# -*- coding: utf-8 -*-
# TODOs
# Watch for changes in `static` and `content` dirs.
# New and changed `static` files are copied to `public`.
# New files in `content` that have an allowed extension and not set to `noindex` result in a full rebuild of the index.
# In `do_GET` only update `content` and generated `index` pages.
import http.server
import socketserver

from pathlib import Path
from shutil import copyfile
from urllib.parse import unquote, urlparse

from logya.core import Logya
from logya.content import add_collections, read, read_all, write_collection
from logya.writer import DocWriter
from logya.util import paths, config


site_index = read_all(paths, config)
add_collections(site_index, config)
L = Logya()
L.init_env()
L.build_index()
L.template.vars['debug'] = True


class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler based class to return resources."""

    def __init__(self, *args):
        super(HTTPRequestHandler, self).__init__(*args, directory=paths.public.as_posix())

    def do_GET(self):
        update_resource(self.path)
        super(HTTPRequestHandler, self).do_GET()


def update_resource(url):
    """Update resource corresponding to given url.

    Static files are updated if necessary, documents are read, parsed and
    written to the appropriate destination file."""

    # Use only the actual path and ignore possible query params issue #3.
    src_url = unquote(urlparse(url).path)
    src_name = src_url.lstrip('/')

    # If a static file is requested update it and return.
    src_static = Path(paths.static, src_name)
    if src_static.is_file():
        dst_static = Path(paths.public, src_name)
        dst_static.parent.mkdir(exist_ok=True)
        if not dst_static.exists() or src_static.stat().st_mtime > dst_static.stat().st_mtime:
            print(f'Update static resource: {dst_static}')
            copyfile(src_static, dst_static)
        return True

    # Rebuild index for unknown HTML file requests.
    if src_url not in site_index and url.endswith(('/', '.html', '.htm')):
        site_index.update(read_all(paths, config))
        add_collections(site_index, config)
    if src_url not in site_index:
        print(f'No content or collection at: {src_url}')
        return

    content = site_index[src_url]
    # Update content document
    if 'doc' in content:
        doc = read(content['path'], paths, config)
        #content['doc'].update(doc)
        DocWriter(paths.public, L.template).write(doc, L.get_doc_template(doc))
        print(f'Refreshed doc at URL: {url}')
        return
    # Update collection page
    if 'docs' in content:
        # FIXME does not show changes made to docs in collection
        path = Path(paths.public, src_name, 'index.html')
        write_collection(path, content, L.template, config)
        print(f'Refreshed collection: {url}')


def serve(args):
    L.template.vars['base_url'] = f'http://{args.host}:{args.port}'
    with socketserver.TCPServer((args.host, args.port), HTTPRequestHandler) as httpd:
        print(f'Serving on {L.template.vars["base_url"]}')
        httpd.serve_forever()