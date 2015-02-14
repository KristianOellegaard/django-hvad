# -*- coding: utf-8 -*-
"""
This code was mostly taken from the django-cms
(https://github.com/divio/django-cms) with permission by it's lead developer.
"""
from django.utils.translation import get_language, activate
from shutil import rmtree as _rmtree
from tempfile import template, mkdtemp, _exists
import warnings

class LanguageOverride(object):
    def __init__(self, language):
        self.newlang = language
        warnings.warn('LanguageOverride is deprecated and will be removed in '
                      'hvad v1.2.0. Please use django.utils.translation.override '
                      'instead', DeprecationWarning, stacklevel=2)

    def __enter__(self):
        self.oldlang = get_language()
        activate(self.newlang)

    def __exit__(self, type, value, traceback):
        activate(self.oldlang)


class TemporaryDirectory:
    """Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everthing contained
    in it are removed.
    """

    def __init__(self, suffix="", prefix=template, dir=None):
        self.name = mkdtemp(suffix, prefix, dir)

    def __enter__(self):
        return self.name

    def cleanup(self):
        if _exists(self.name):
            _rmtree(self.name)

    def __exit__(self, exc, value, tb):
        self.cleanup()


class UserLoginContext(object):
    def __init__(self, testcase, **kwargs):
        self.testcase = testcase
        self.kwargs = kwargs
        
    def __enter__(self):
        self.testcase.assertTrue(self.testcase.client.login(**self.kwargs))
        
    def __exit__(self, exc, value, tb):
        self.testcase.client.logout()
