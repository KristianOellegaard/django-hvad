# -*- coding: utf-8 -*-
import shutil
import tempfile
import warnings

#===============================================================================

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

#===============================================================================

class UserLoginContext(object):
    def __init__(self, testcase, **kwargs):
        self.testcase = testcase
        self.kwargs = kwargs
        
    def __enter__(self):
        self.testcase.assertTrue(self.testcase.client.login(**self.kwargs))
        
    def __exit__(self, exc, value, tb):
        self.testcase.client.logout()

#===============================================================================

class AssertThrowsWarningContext(object):
    def __init__(self, test_case, klass, number):
        self.test_case = test_case
        self.klass = klass
        self.number = number
        self.ctx = warnings.catch_warnings(record=True)

    def __enter__(self):
        self.warnings = self.ctx.__enter__()
        warnings.resetwarnings()
        warnings.simplefilter('always')

    def __exit__(self, type, value, traceback):
        self.test_case.assertEqual(
            len(self.warnings), self.number, "%d warnings thrown, %d expected" % (
                len(self.warnings), self.number
            )
        )
        for warning in self.warnings:
            self.test_case.assertTrue(issubclass(warning.category, self.klass),
                                      '%s warning thrown, %s expected' %
                                      (warning.category.__name__, self.klass.__name__))
        self.ctx.__exit__(type, value, traceback)
