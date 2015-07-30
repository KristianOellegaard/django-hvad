import django
from django.utils.functional import cached_property
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


class HvadTestCase(TestCase):
    def setUp(self):

        if hasattr(self, 'create_fixtures'):
            self.create_fixtures()

    @cached_property
    def request_factory(self):
        return RequestFactory()

    def login_user_context(self, username):
        return UserLoginContext(self, username=username, password=username)

    def assertThrowsWarning(self, klass, number=1):
        return _AssertThrowsWarningContext(self, klass, number)

    def assertSavedObject(self, obj, language, **kwargs):
        'Checks the object was saved in given language with given attributes'
        self.assertEqual(language, kwargs.pop('language_code', language),
                         'Test error: mismatching language and language_code.')
        for key, value in kwargs.items():
            self.assertEqual(getattr(obj, key), value)
        self.assertEqual(obj.language_code, language)
        self.assertCountEqual(
            obj.__class__.objects.language(language).filter(**kwargs).values_list('pk', flat=True),
            [obj.pk]
        )

# method was renamed from assertItemsEqual in Python 3
if not hasattr(HvadTestCase, 'assertCountEqual'):
    HvadTestCase.assertCountEqual = HvadTestCase.assertItemsEqual
