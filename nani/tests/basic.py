# -*- coding: utf-8 -*-
from __future__ import with_statement
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
            en = Normal.objects.create(
                shared_field="shared",
                translated_field='English',
                language_code='en'
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


class BasicQueryTest(SingleNormalTestCase):
    def test_basic(self):
        en = self.get_obj()
        with self.assertNumQueries(1):
            queried = Normal.objects.get(pk=en.pk, language_code='en')
            self.assertEqual(queried.shared_field, en.shared_field)
            self.assertEqual(queried.translated_field, en.translated_field)
            self.assertEqual(queried.language_code, en.language_code)


class DeleteLanguageCodeTest(SingleNormalTestCase):
    def test_delete_language_code(self):
        en = self.get_obj()
        self.assertRaises(AttributeError, delattr, en, 'language_code')