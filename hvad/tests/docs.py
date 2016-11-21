# -*- coding: utf-8 -*-
from django.test.testcases import TestCase
from hvad.test_utils.context_managers import TemporaryDirectory
import os
import sys


ROOT_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
DOCS_DIR = os.path.abspath(os.path.join(ROOT_DIR, 'docs'))

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
