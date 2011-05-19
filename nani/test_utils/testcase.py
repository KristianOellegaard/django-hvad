from django.conf import settings
from django.core.signals import request_started
from django.db import reset_queries, connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.test import testcases
from nani.test_utils.context_managers import UserLoginContext
from nani.test_utils.request_factory import RequestFactory
import sys


class _AssertNumQueriesContext(object):
    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        self.connection = connection

    def __enter__(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.starting_queries = len(self.connection.queries)
        request_started.disconnect(reset_queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        settings.DEBUG = self.old_debug
        request_started.connect(reset_queries)
        if exc_type is not None:
            return

        final_queries = len(self.connection.queries)
        executed = final_queries - self.starting_queries

        self.test_case.assertEqual(
            executed, self.num, "%d queries executed, %d expected" % (
                executed, self.num
            )
        )


if hasattr(testcases.TestCase, 'assertNumQueries'):
    TestCase = testcases.TestCase
else:
    class TestCase(testcases.TestCase):
        def assertNumQueries(self, num, func=None, *args, **kwargs):
            if hasattr(testcases.TestCase, 'assertNumQueries'):
                return super(TestCase, self).assertNumQueries(num, func, *args, **kwargs)
            return self._assertNumQueries(num, func, *args, **kwargs)
    
        def _assertNumQueries(self, num, func=None, *args, **kwargs):
            """
            Backport from Django 1.3 for Django 1.2
            """
            using = kwargs.pop("using", DEFAULT_DB_ALIAS)
            connection = connections[using]
    
            context = _AssertNumQueriesContext(self, num, connection)
            if func is None:
                return context
    
            # Basically emulate the `with` statement here.
    
            context.__enter__()
            try:
                func(*args, **kwargs)
            except:
                context.__exit__(*sys.exc_info())
                raise
            else:
                context.__exit__(*sys.exc_info())


class NaniTestCase(TestCase):
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