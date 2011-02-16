# -*- coding: utf-8 -*-
from __future__ import with_statement
from django.db.models.query_utils import Q
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase, SingleNormalTestCase
from testproject.app.models import Normal


class OptionsTest(NaniTestCase):
    def test_options(self):
        opts = Normal._meta
        self.assertTrue(hasattr(opts, 'translations_model'))
        self.assertTrue(hasattr(opts, 'translations_accessor'))
        relmodel = Normal._meta.get_field_by_name(opts.translations_accessor)[0].model
        self.assertEqual(relmodel, opts.translations_model)


class CreateTest(NaniTestCase):
    def test_create(self):
        with self.assertNumQueries(2):
            en = Normal.objects.language('en').create(
                shared_field="shared",
                translated_field='English',
            )
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
        

class TranslatedTest(SingleNormalTestCase):
    def test_translate(self):
        SHARED_EN = 'shared'
        TRANS_EN = 'English'
        SHARED_JA = 'shared'
        TRANS_JA = u'日本語'
        en = self.get_obj()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 1)
        self.assertEqual(en.shared_field, SHARED_EN)
        self.assertEqual(en.translated_field, TRANS_EN)
        ja = en
        ja.language_code = 'ja'
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        self.assertEqual(ja.shared_field, SHARED_JA)
        self.assertEqual(ja.translated_field, TRANS_EN)
        ja.translated_field = TRANS_JA
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        self.assertEqual(ja.shared_field, SHARED_JA)
        self.assertEqual(ja.translated_field, TRANS_JA)
        with LanguageOverride('en'):
            obj = self.reload(ja)
            self.assertEqual(obj.shared_field, SHARED_EN)
            self.assertEqual(obj.translated_field, TRANS_EN)
        with LanguageOverride('ja'):
            obj = self.reload(en)
            self.assertEqual(obj.shared_field, SHARED_JA)
            self.assertEqual(obj.translated_field, TRANS_JA)
        

class GetTest(SingleNormalTestCase):
    def test_get(self):
        en = self.get_obj()
        with self.assertNumQueries(1):
            got = Normal.objects.get(pk=en.pk, language_code='en')
        with self.assertNumQueries(0):
            self.assertEqual(got.shared_field, "shared")
            self.assertEqual(got.translated_field, "English")
            self.assertEqual(got.language_code, "en")

class GetByLanguageTest(NaniTestCase):
    fixtures = ['double_normal.json']
    
    data = {
        1: {
            'shared_field': 'Shared1',
            'translated_field_en': 'English1',
            'translated_field_ja': u'日本語一',
        },
        2: {
            'shared_field': 'Shared2',
            'translated_field_en': 'English2',
            'translated_field_ja': u'日本語二',
        },
    }
    
    def test_args(self):
        with LanguageOverride('en'):
            q = Q(language_code='ja', pk=1)
            obj = Normal.objects.get(q)
            self.assertEqual(obj.shared_field, self.data[1]['shared_field'])
            self.assertEqual(obj.translated_field, self.data[1]['translated_field_ja'])
    
    def test_kwargs(self):
        with LanguageOverride('en'):
            kwargs = {'language_code':'ja', 'pk':1}
            obj = Normal.objects.get(**kwargs)
            self.assertEqual(obj.shared_field, self.data[1]['shared_field'])
            self.assertEqual(obj.translated_field, self.data[1]['translated_field_ja'])
        
    def test_language(self):
        with LanguageOverride('en'):
            obj = Normal.objects.language('ja').get(pk=1)
            self.assertEqual(obj.shared_field, self.data[1]['shared_field'])
            self.assertEqual(obj.translated_field, self.data[1]['translated_field_ja'])

class BasicQueryTest(SingleNormalTestCase):
    def test_basic(self):
        en = self.get_obj()
        with self.assertNumQueries(1):
            queried = Normal.objects.language('en').get(pk=en.pk)
            self.assertEqual(queried.shared_field, en.shared_field)
            self.assertEqual(queried.translated_field, en.translated_field)
            self.assertEqual(queried.language_code, en.language_code)


class DeleteLanguageCodeTest(SingleNormalTestCase):
    def test_delete_language_code(self):
        en = self.get_obj()
        self.assertRaises(AttributeError, delattr, en, 'language_code')