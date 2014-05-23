# -*- coding: utf-8 -*-
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.data import DOUBLE_NORMAL
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal
from hvad.test_utils.fixtures import TwoTranslatedNormalMixin
from hvad.exceptions import WrongManager

class FallbackTests(HvadTestCase, TwoTranslatedNormalMixin):
    def test_single_instance_fallback(self):
        # fetch an object in a language that does not exist
        with LanguageOverride('de'):
            with self.assertNumQueries(2):
                obj = Normal.objects.untranslated().use_fallbacks('en', 'ja').get(pk=1)
                self.assertEqual(obj.language_code, 'en')
                self.assertEqual(obj.translated_field, 'English1')

    def test_shared_only(self):
        with LanguageOverride('de'):
            with self.assertNumQueries(1):
                obj = Normal.objects.untranslated().get(pk=1)
                self.assertEqual(obj.shared_field, 'Shared1')
            with self.assertNumQueries(1):
                self.assertRaises(AttributeError, getattr, obj, 'translated_field')

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
                self.assertEqual(len(objs), 3)


class FallbackFilterTests(HvadTestCase, TwoTranslatedNormalMixin):
    def test_simple_filter_untranslated(self):
        with LanguageOverride('en'):
            qs = Normal.objects.untranslated() .filter(shared_field__contains='2')
            with self.assertNumQueries(1):
                self.assertEqual(qs.count(), 1)
            with self.assertNumQueries(1):
                obj = qs[0]
                self.assertEqual(obj.shared_field, DOUBLE_NORMAL[2]['shared_field'])
            with self.assertNumQueries(1):
                self.assertEqual(obj.translated_field, DOUBLE_NORMAL[2]['translated_field_en'])

    def test_simple_filter_fallbacks(self):
        qs = (Normal.objects.untranslated()
                            .use_fallbacks('en', 'ja')
                            .filter(shared_field__contains='2'))
        with self.assertNumQueries(1):
            self.assertEqual(qs.count(), 1)
        with self.assertNumQueries(2):
            obj = qs[0]
        with self.assertNumQueries(0):
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[2]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[2]['translated_field_en'])

        qs = (Normal.objects.untranslated()
                            .use_fallbacks('ja', 'en')
                            .filter(shared_field__contains='1'))
        with self.assertNumQueries(1):
            self.assertEqual(qs.count(), 1)
        with self.assertNumQueries(2):
            obj = qs[0]
        with self.assertNumQueries(0):
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])

    def test_translated_filter(self):
        with self.assertRaises(WrongManager):
            qs = Normal.objects.untranslated().filter(translated_field__contains='English')


class FallbackCachingTests(HvadTestCase, TwoTranslatedNormalMixin):
    def _try_all_cache_using_methods(self, qs, length):
        with self.assertNumQueries(0):
            x = 0
            for obj in qs: x += 1
            self.assertEqual(x, length)
        with self.assertNumQueries(0):
            qs[0]
        with self.assertNumQueries(0):
            self.assertEqual(qs.exists(), length != 0)
        with self.assertNumQueries(0):
            self.assertEqual(qs.count(), length)
        with self.assertNumQueries(0):
            self.assertEqual(len(qs), length)
        with self.assertNumQueries(0):
            self.assertEqual(bool(qs), length != 0)

    def test_iter_caches(self):
        index = 0
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=1)
        for obj in qs:
            index += 1
        self.assertEqual(index, 1)
        self._try_all_cache_using_methods(qs, 1)

    def test_pickling_caches(self):
        import pickle
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=1)
        pickle.dumps(qs)
        self._try_all_cache_using_methods(qs, 1)

    def test_len_caches(self):
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=1)
        self.assertEqual(len(qs), 1)
        self._try_all_cache_using_methods(qs, 1)

    def test_bool_caches(self):
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=1)
        self.assertTrue(qs)
        self._try_all_cache_using_methods(qs, 1)


class FallbackIterTests(HvadTestCase, TwoTranslatedNormalMixin):
    def test_simple_iter_fallbacks(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                index = 0
                for obj in Normal.objects.untranslated():
                    index += 1
                    self.assertEqual(obj.shared_field, DOUBLE_NORMAL[index]['shared_field'])
                    with self.assertNumQueries(1):
                        self.assertEqual(obj.translated_field, DOUBLE_NORMAL[index]['translated_field_en'])

    def test_simple_iter_fallbacks(self):
        with self.assertNumQueries(2):
            index = 0
            for obj in Normal.objects.untranslated().use_fallbacks('en', 'ja'):
                index += 1
                self.assertEqual(obj.shared_field, DOUBLE_NORMAL[index]['shared_field'])
                self.assertEqual(obj.translated_field, DOUBLE_NORMAL[index]['translated_field_en'])

        with self.assertNumQueries(2):
            index = 0
            for obj in Normal.objects.untranslated().use_fallbacks('ja', 'en'):
                index += 1
                self.assertEqual(obj.shared_field, DOUBLE_NORMAL[index]['shared_field'])
                self.assertEqual(obj.translated_field, DOUBLE_NORMAL[index]['translated_field_ja'])

    def test_iter_unique_reply(self):
        # Make sure .all() only returns unique rows
        self.assertEqual(len(Normal.objects.untranslated().use_fallbacks('en', 'ja').all()),
                         len(Normal.objects.untranslated()))



class FallbackValuesListTests(HvadTestCase, TwoTranslatedNormalMixin):
    def test_values_list_shared(self):
        values = (Normal.objects.untranslated()
                                .use_fallbacks('en', 'ja')
                                .values_list('shared_field', flat=True))
        with self.assertNumQueries(1):
            values_list = list(values)
            self.assertCountEqual(values_list, [DOUBLE_NORMAL[1]['shared_field'], DOUBLE_NORMAL[2]['shared_field']])

    def test_values_list_translated(self):
        with self.assertRaises(WrongManager):
            values = Normal.objects.untranslated().values_list('translated_field', flat=True)


class FallbackValuesTests(HvadTestCase, TwoTranslatedNormalMixin):
    def test_values_shared(self):
        values = (Normal.objects.untranslated()
                                .use_fallbacks('en', 'ja')
                                .values('shared_field'))
        with self.assertNumQueries(1):
            values_list = list(values)
            check = [
                {'shared_field': DOUBLE_NORMAL[1]['shared_field']},
                {'shared_field': DOUBLE_NORMAL[2]['shared_field']},
            ]
            self.assertCountEqual(values_list, check)

    def test_values_translated(self):
        with self.assertRaises(WrongManager):
            values = Normal.objects.untranslated().values('translated_field')


class FallbackInBulkTests(HvadTestCase, TwoTranslatedNormalMixin):
    def test_in_bulk_untranslated(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                result = Normal.objects.untranslated().in_bulk([1, 2])
            with self.assertNumQueries(0):
                self.assertCountEqual((1, 2), result)
                self.assertEqual(result[1].shared_field, DOUBLE_NORMAL[1]['shared_field'])
            with self.assertNumQueries(1):
                self.assertEqual(result[1].translated_field, DOUBLE_NORMAL[1]['translated_field_en'])
            with self.assertNumQueries(0):
                self.assertEqual(result[1].language_code, 'en')
        with LanguageOverride('ja'):
            with self.assertNumQueries(0):
                self.assertEqual(result[2].shared_field, DOUBLE_NORMAL[2]['shared_field'])
            with self.assertNumQueries(1):
                self.assertEqual(result[2].translated_field, DOUBLE_NORMAL[2]['translated_field_ja'])
            with self.assertNumQueries(0):
                self.assertEqual(result[2].language_code, 'ja')

    def test_in_bulk_fallbacks(self):
        with self.assertNumQueries(2):
            result = Normal.objects.untranslated().use_fallbacks('en', 'ja').in_bulk([1, 2])
        with self.assertNumQueries(0):
            self.assertCountEqual((1, 2), result)
            self.assertEqual(result[1].shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(result[1].translated_field, DOUBLE_NORMAL[1]['translated_field_en'])
            self.assertEqual(result[1].language_code, 'en')
            self.assertEqual(result[2].shared_field, DOUBLE_NORMAL[2]['shared_field'])
            self.assertEqual(result[2].translated_field, DOUBLE_NORMAL[2]['translated_field_en'])
            self.assertEqual(result[2].language_code, 'en')


class FallbackNotImplementedTests(HvadTestCase):
    def test_defer(self):
        baseqs = Normal.objects.untranslated()
        self.assertRaises(NotImplementedError, baseqs.defer, 'shared_field')
        self.assertRaises(NotImplementedError, baseqs.only)
        self.assertRaises(NotImplementedError, baseqs.aggregate)
        self.assertRaises(NotImplementedError, baseqs.annotate)
