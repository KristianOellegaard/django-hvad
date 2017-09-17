from django.utils import translation
from hvad.utils import (translation_rater, get_cached_translation, set_cached_translation,
                        get_translation, load_translation)
from hvad.test_utils.data import NORMAL
from hvad.test_utils.fixtures import NormalFixture
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, NormalProxy


class TranslationRaterTests(HvadTestCase):
    def test_default_rater(self):
        with self.settings(HVAD={'DEFAULT_LANGUAGE': 'aa', 'FALLBACK_LANGUAGES': ('bb', 'cc', 'dd')}):
            with translation.override('ee'):
                rater = translation_rater()
        result = sorted([Normal._meta.translations_model(language_code=lang)
                         for lang in ('aa', 'bb', 'cc', 'dd', 'ee', 'ff')], key=rater)
        self.assertEqual([trobj.language_code for trobj in result], ['ff', 'dd', 'cc', 'bb', 'aa', 'ee'])

    def test_specified_rater(self):
        rater = translation_rater('cc', 'aa', 'bb')
        result = sorted([Normal._meta.translations_model(language_code=lang)
                         for lang in ('aa', 'bb', 'cc', 'dd')], key=rater)
        self.assertEqual([trobj.language_code for trobj in result], ['dd', 'bb', 'aa', 'cc'])

class TranslationAccessorTests(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_get_cached_translation(self):
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            self.assertIs(get_cached_translation(obj), None)
            self.assertFalse(obj._meta.get_field('_hvad_query').is_cached(obj))

            obj.translate('sr')
            self.assertIsNot(get_cached_translation(obj), None)
            self.assertEqual(get_cached_translation(obj).language_code, 'sr')

        old = set_cached_translation(obj, obj.translations.get_language('ja'))
        with self.assertNumQueries(0):
            self.assertEqual(old.language_code, 'sr')
            self.assertEqual(obj.language_code, 'ja')
            self.assertEqual(get_cached_translation(obj).language_code, 'ja')

            set_cached_translation(obj, None)
            self.assertIs(get_cached_translation(obj), None)
            self.assertFalse(obj._meta.get_field('_hvad_query').is_cached(obj))

        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            self.assertEqual(get_cached_translation(obj).language_code, 'en')

    def test_get_translation(self):
        # no translation loaded
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            translation = get_translation(obj, 'ja')
            self.assertEqual(translation.language_code, 'ja')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['ja'])

        # translation loaded (it should be ignored)
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        obj.translated_field = 'changed'
        with self.assertNumQueries(1):
            translation = get_translation(obj, 'en')
            self.assertEqual(translation.language_code, 'en')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['en'])

        # with prefetching
        obj = Normal.objects.untranslated().prefetch_related('translations').get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            translation = get_translation(obj, 'ja')
            self.assertEqual(translation.language_code, 'ja')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['ja'])

        # with prefetching and non-existent translation
        with self.assertNumQueries(0):
            self.assertRaises(Normal.DoesNotExist, get_translation, obj, 'xx')

    def test_load_translation_normal(self):
        # no translation loaded, one exists in db for language
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            translation = load_translation(obj, 'en')
            self.assertIsNot(translation.pk, None)
            self.assertEqual(translation.language_code, 'en')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['en'])

        # no translation loaded, none exists for language
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            translation = load_translation(obj, 'xx')
            self.assertIsInstance(translation, Normal._meta.translations_model)
            self.assertIs(translation.pk, None)
            self.assertEqual(translation.language_code, 'xx')

        # no translation is loaded, prefetch enabled
        obj = Normal.objects.untranslated().prefetch_related('translations').get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            translation = load_translation(obj, 'ja')
            self.assertIsNot(translation.pk, None)
            self.assertEqual(translation.language_code, 'ja')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['ja'])

        # translation loaded, it should be used regardless of language
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            translation = load_translation(obj, 'ja')
            self.assertIsNot(translation.pk, None)
            self.assertEqual(translation.language_code, 'en')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['en'])

    def test_load_translation_enforce(self):
        # correct translation loaded, it should be used
        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            translation = load_translation(obj, 'ja', enforce=True)
            self.assertIsNot(translation.pk, None)
            self.assertEqual(translation.language_code, 'ja')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['ja'])

        # wrong translation loaded, it should be reloaded
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            translation = load_translation(obj, 'ja', enforce=True)
            self.assertIsNot(translation.pk, None)
            self.assertEqual(translation.language_code, 'ja')
            self.assertEqual(translation.translated_field, NORMAL[1].translated_field['ja'])

        # wrong translation loaded, reloading fails, it should be created
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            translation = load_translation(obj, 'sr', enforce=True)
            self.assertIs(translation.pk, None)
            self.assertEqual(translation.language_code, 'sr')
