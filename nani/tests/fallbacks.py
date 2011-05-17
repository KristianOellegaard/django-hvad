# -*- coding: utf-8 -*-
from django.db import connection
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal
from nani.test_utils.fixtures import TwoTranslatedNormalMixin


class FallbackTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_single_instance_fallback(self):
        # fetch an object in a language that does not exist
        with LanguageOverride('de'):
            with self.assertNumQueries(2):
                obj = Normal.objects.untranslated().use_fallbacks('en', 'ja').get(pk=1)
                self.assertEqual(obj.language_code, 'en')
                self.assertEqual(obj.translated_field, 'English1')
    
    def test_shared_only(self):
        with LanguageOverride('de'):
            with self.assertNumQueries(2):
                obj = Normal.objects.untranslated().get(pk=1)
                self.assertEqual(obj.shared_field, 'Shared1')
                self.assertRaises(Normal._meta.translations_model.DoesNotExist,
                                  getattr, obj, 'translated_field')
