# -*- coding: utf-8 -*-
import shutil

from shutil import copytree

from logya.core import Logya
from logya.content import filepath, write_collection, write_doc


def generate(dir_site: str, verbose: bool, keep: bool, **kwargs):
    L = Logya(dir_site=dir_site, verbose=verbose)
    L.build()

    if not keep:
        print('Remove existing public directory.')
        shutil.rmtree(L.paths.public, ignore_errors=True)

    print(f'Generate site in directory: {L.paths.public.as_posix()}')
    if L.paths.static.exists():
        print('Copy static files.')
        copytree(L.paths.static, L.paths.public, dirs_exist_ok=True)  # dirs_exist_ok requires Python 3.8

    print('Write pages.')
    for url, content in L.doc_index.items():
        path_dst = filepath(L.paths.public, url)
        L.info(f'Write content: {path_dst}')
        write_doc(path_dst, content, L.settings)

    for url, content in L.collection_index.items():
        path_dst = filepath(L.paths.public, url)
        L.info(f'Write collection: {path_dst}')
        write_collection(path_dst, content)
