import django
from django.test.testcases import TestCase
from django.test.client import RequestFactory
from hvad.test_utils.context_managers import UserLoginContext
import warnings


def minimumDjangoVersion(*args):
    return (lambda x: x) if django.VERSION >= args else (lambda x: 'disabled')
def maximumDjangoVersion(*args):
    return (lambda x: x) if django.VERSION < args else (lambda x: 'disabled')


class _AssertThrowsWarningContext(object):
    def __init__(self, test_case, klass, number):
        self.test_case = test_case
        self.klass = klass
        self.number = number
        self.ctx = warnings.catch_warnings(record=True)

    def __enter__(self):
        self.warnings = self.ctx.__enter__()
        warnings.simplefilter('always')

    def __exit__(self, type, value, traceback):
        self.ctx.__exit__(type, value, traceback)
        self.test_case.assertEqual(
            len(self.warnings), self.number, "%d warnings thrown, %d expected" % (
                len(self.warnings), self.number
            )
        )
        for warning in self.warnings:
            self.test_case.assertTrue(issubclass(warning.category, self.klass),
                                      '%s warning thrown, %s expected' %
                                      (warning.category.__name__, self.klass.__name__))


class HvadTestCase(TestCase):
    def setUp(self):
        if callable(getattr(self, 'create_fixtures', None)):
            self.create_fixtures()

    @property
    def request_factory(self):
        if not hasattr(self, '_request_factory'):
            self._request_factory = RequestFactory()
        return self._request_factory
    
    def reload(self, obj):
        model = obj.__class__
        qs = model.objects
        if callable(getattr(qs, 'language', None)):
            qs = qs.language()
        return qs.get(**{obj._meta.pk.name: obj.pk})

    def login_user_context(self, **kwargs):
        return UserLoginContext(self, **kwargs)

    def assertThrowsWarning(self, klass, number=1):
        return _AssertThrowsWarningContext(self, klass, number)

# method was renamed from assertItemsEqual in Python 3
if not hasattr(HvadTestCase, 'assertCountEqual'):
    HvadTestCase.assertCountEqual = HvadTestCase.assertItemsEqual
