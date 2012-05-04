# -*- coding: utf-8 -*-
from django.db import connection
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal
from hvad.test_utils.fixtures import TwoTranslatedNormalMixin


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
    
    def test_mixed_fallback(self):
        with LanguageOverride('de'):
            pk = Normal.objects.language('ja').create(
                shared_field='shared3',
                translated_field=u'日本語三',
            ).pk
            with self.assertNumQueries(2):
                objs = list(Normal.objects.untranslated().use_fallbacks('en', 'ja'))
                self.assertEqual(len(objs), 3)
                obj = dict([(obj.pk, obj) for obj in objs])[pk]
                self.assertEqual(obj.language_code, 'ja')
            with self.assertNumQueries(2):
                objs = list(Normal.objects.untranslated().use_fallbacks('en'))
                self.assertEqual(len(objs), 2)
#                We dont return unstranslated instances in django-hvad
#                obj = dict([(obj.pk, obj) for obj in objs])[pk]
#                cached = getattr(obj, obj._meta.translations_cache, None)
#                self.assertEqual(cached, None)