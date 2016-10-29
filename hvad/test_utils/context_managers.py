# -*- coding: utf-8 -*-
"""
This code was mostly taken from the django-cms
(https://github.com/divio/django-cms) with permission by it's lead developer.
"""
import shutil
import tempfile

try:
    from tempfile import TemporaryDirectory
except ImportError:
    class TemporaryDirectory(object):
        def __init__(self, suffix='', prefix='tmp', dir=None):
            self.name = tempfile.mkdtemp(suffix, prefix, dir)

        def __enter__(self):
            return self.name

        def __exit__(self, exc, value, tb):
            try:
                shutil.rmtree(self.name)
            except OSError as err:
                if err.errno != 2:
                    raise


class UserLoginContext(object):
    def __init__(self, testcase, **kwargs):
        self.testcase = testcase
        self.kwargs = kwargs
        
    def __enter__(self):
        self.testcase.assertTrue(self.testcase.client.login(**self.kwargs))
        
    def __exit__(self, exc, value, tb):
        self.testcase.client.logout()
