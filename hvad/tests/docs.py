# -*- coding: utf-8 -*-
from __future__ import with_statement
import sys
from django.test.testcases import TestCase
from shutil import rmtree
from tempfile import template, mkdtemp, _exists
import os
from hvad.compat.string_io import StringIO


ROOT_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
DOCS_DIR = os.path.abspath(os.path.join(ROOT_DIR, 'docs'))

class TemporaryDirectory:
    """Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained
    in it are removed.
    """

    def __init__(self, suffix="", prefix=template, dir=None):
        self.name = mkdtemp(suffix, prefix, dir)

    def __enter__(self):
        return self.name

    def cleanup(self):
        if _exists(self.name):
            rmtree(self.name)

    def __exit__(self, exc, value, tb):
        self.cleanup()


class DocumentationTests(TestCase):
    """
    Can be mixed in with a unittest.TestCase class to ensure documentation
    builds properly.
    """
    def test_docs_build(self):
        from sphinx.application import Sphinx
        with TemporaryDirectory() as OUT_DIR:
            with open(os.path.join(OUT_DIR, 'log'), 'w+') as fobj:
                app = Sphinx(
                    DOCS_DIR,
                    DOCS_DIR,
                    OUT_DIR,
                    OUT_DIR,
                    'html',
                    warningiserror=True,
                    status=fobj,
                )
                try:
                    app.build()
                except Exception:
                    e = sys.exc_info()[1]
                    fobj.seek(0)
                    self.fail('%s\n%s' % (e, fobj.read()))
