from django.utils.functional import cached_property
from django.test.testcases import TestCase
from django.test.client import RequestFactory
from hvad.test_utils.context_managers import UserLoginContext, AssertThrowsWarningContext

__all__ = ('HvadTestCase',)

#===============================================================================

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
        return AssertThrowsWarningContext(self, klass, number)

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
