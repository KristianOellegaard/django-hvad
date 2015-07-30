# -*- coding: utf-8 -*-
from django.utils import translation
from hvad.test_utils.data import NORMAL
from hvad.test_utils.testcase import HvadTestCase, minimumDjangoVersion
from hvad.test_utils.project.app.models import Normal
from hvad.test_utils.fixtures import NormalFixture
from hvad.exceptions import WrongManager
from hvad.manager import LEGACY_FALLBACKS

class FallbackDeprecationTests(HvadTestCase):
    @minimumDjangoVersion(1, 6)
    def test_untranslated_fallbacks_deprecation(self):
        with self.assertThrowsWarning(DeprecationWarning):
            Normal.objects.untranslated().use_fallbacks('en')

class FallbackTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_single_instance_fallback(self):
        # fetch an object in a language that does not exist
        with translation.override('de'):
            with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
                obj = Normal.objects.untranslated().use_fallbacks('en', 'ja').get(pk=self.normal_id[1])
                self.assertEqual(obj.language_code, 'en')
                self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])

    def test_deferred_fallbacks(self):
        with translation.override('de'):
            qs = Normal.objects.untranslated().use_fallbacks('ru', None, 'en')
        with translation.override('ja'):
            with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
                obj = qs.get(pk=self.normal_id[1])
                self.assertEqual(obj.language_code, 'ja')
                self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])
        with translation.override('en'):
            with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
                obj = qs.get(pk=self.normal_id[1])
                self.assertEqual(obj.language_code, 'en')
                self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])

    def test_shared_only(self):
        with translation.override('de'):
            with self.assertNumQueries(1):
                obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
                self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
            with self.assertNumQueries(1):
                self.assertRaises(AttributeError, getattr, obj, 'translated_field')

    def test_mixed_fallback(self):
        with translation.override('de'):
            pk = Normal.objects.language('ja').create(
                shared_field='shared_field',
                translated_field=u'日本語三',
            ).pk
            with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
                objs = list(Normal.objects.untranslated().use_fallbacks('en', 'ja'))
                self.assertEqual(len(objs), 3)
                obj = dict([(obj.pk, obj) for obj in objs])[pk]
                self.assertEqual(obj.language_code, 'ja')
            with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
                objs = list(Normal.objects.untranslated().use_fallbacks('en'))
                self.assertEqual(len(objs), 3)


class FallbackFilterTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_simple_filter_untranslated(self):
        with translation.override('en'):
            qs = Normal.objects.untranslated() .filter(shared_field__contains='2')
            with self.assertNumQueries(1):
                self.assertEqual(qs.count(), 1)
            with self.assertNumQueries(1):
                obj = qs[0]
                self.assertEqual(obj.shared_field, NORMAL[2].shared_field)
            with self.assertNumQueries(1):
                self.assertEqual(obj.translated_field, NORMAL[2].translated_field['en'])

    def test_simple_filter_fallbacks(self):
        qs = (Normal.objects.untranslated()
                            .use_fallbacks('en', 'ja')
                            .filter(shared_field__contains='2'))
        with self.assertNumQueries(1):
            self.assertEqual(qs.count(), 1)
        with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
            obj = qs[0]
        with self.assertNumQueries(0):
            self.assertEqual(obj.shared_field, NORMAL[2].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[2].translated_field['en'])

        qs = (Normal.objects.untranslated()
                            .use_fallbacks('ja', 'en')
                            .filter(shared_field__contains='1'))
        with self.assertNumQueries(1):
            self.assertEqual(qs.count(), 1)
        with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
            obj = qs[0]
        with self.assertNumQueries(0):
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])

    def test_translated_filter(self):
        with self.assertRaises(WrongManager):
            Normal.objects.untranslated().filter(translated_field__contains='English')


class FallbackCachingTests(HvadTestCase, NormalFixture):
    normal_count = 2

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
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=self.normal_id[1])
        for obj in qs:
            index += 1
        self.assertEqual(index, 1)
        self._try_all_cache_using_methods(qs, 1)

    def test_pickling_caches(self):
        import pickle
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=self.normal_id[1])
        pickle.dumps(qs)
        self._try_all_cache_using_methods(qs, 1)

    def test_len_caches(self):
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=self.normal_id[1])
        self.assertEqual(len(qs), 1)
        self._try_all_cache_using_methods(qs, 1)

    def test_bool_caches(self):
        qs = Normal.objects.untranslated().use_fallbacks().filter(pk=self.normal_id[1])
        self.assertTrue(qs)
        self._try_all_cache_using_methods(qs, 1)


class FallbackIterTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_simple_iter_no_fallbacks(self):
        with translation.override('en'):
            with self.assertNumQueries(1):
                objs = list(Normal.objects.untranslated().order_by('pk'))
            for index, obj in enumerate(objs, 1):
                self.assertEqual(obj.shared_field, NORMAL[index].shared_field)
                with self.assertNumQueries(1):
                    self.assertEqual(obj.translated_field, NORMAL[index].translated_field['en'])

    def test_simple_iter_fallbacks(self):
        with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
            for index, obj in enumerate(Normal.objects.untranslated().use_fallbacks('en', 'ja').order_by('pk'), 1):
                self.assertEqual(obj.shared_field, NORMAL[index].shared_field)
                self.assertEqual(obj.translated_field, NORMAL[index].translated_field['en'])

        with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
            for index, obj in enumerate(Normal.objects.untranslated().use_fallbacks('ja', 'en').order_by('pk'), 1):
                self.assertEqual(obj.shared_field, NORMAL[index].shared_field)
                self.assertEqual(obj.translated_field, NORMAL[index].translated_field['ja'])

    def test_iter_unique_reply(self):
        # Make sure .all() only returns unique rows
        self.assertEqual(len(Normal.objects.untranslated().use_fallbacks('en', 'ja').all()),
                         len(Normal.objects.untranslated()))



class FallbackValuesListTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_values_list_shared(self):
        values = (Normal.objects.untranslated()
                                .use_fallbacks('en', 'ja')
                                .values_list('shared_field', flat=True))
        with self.assertNumQueries(1):
            values_list = list(values)
            self.assertCountEqual(values_list, [NORMAL[1].shared_field, NORMAL[2].shared_field])

    def test_values_list_translated(self):
        with self.assertRaises(WrongManager):
            Normal.objects.untranslated().values_list('translated_field', flat=True)


class FallbackValuesTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_values_shared(self):
        values = (Normal.objects.untranslated()
                                .use_fallbacks('en', 'ja')
                                .values('shared_field'))
        with self.assertNumQueries(1):
            values_list = list(values)
            check = [
                {'shared_field': NORMAL[1].shared_field},
                {'shared_field': NORMAL[2].shared_field},
            ]
            self.assertCountEqual(values_list, check)

    def test_values_translated(self):
        with self.assertRaises(WrongManager):
            Normal.objects.untranslated().values('translated_field')


class FallbackInBulkTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_in_bulk_untranslated(self):
        pk1, pk2 = self.normal_id[1], self.normal_id[2]
        with translation.override('en'):
            with self.assertNumQueries(1):
                result = Normal.objects.untranslated().in_bulk([pk1, pk2])
            with self.assertNumQueries(0):
                self.assertCountEqual((pk1, pk2), result)
                self.assertEqual(result[pk1].shared_field, NORMAL[1].shared_field)
            with self.assertNumQueries(1):
                self.assertEqual(result[pk1].translated_field, NORMAL[1].translated_field['en'])
            with self.assertNumQueries(0):
                self.assertEqual(result[pk1].language_code, 'en')
        with translation.override('ja'):
            with self.assertNumQueries(0):
                self.assertEqual(result[pk2].shared_field, NORMAL[2].shared_field)
            with self.assertNumQueries(1):
                self.assertEqual(result[pk2].translated_field, NORMAL[2].translated_field['ja'])
            with self.assertNumQueries(0):
                self.assertEqual(result[pk2].language_code, 'ja')

    def test_in_bulk_fallbacks(self):
        pk1, pk2 = self.normal_id[1], self.normal_id[2]
        with self.assertNumQueries(2 if LEGACY_FALLBACKS else 1):
            result = (Normal.objects.untranslated()
                                    .use_fallbacks('en', 'ja')
                                    .in_bulk([pk1, pk2]))
        with self.assertNumQueries(0):
            self.assertCountEqual((pk1, pk2), result)
            self.assertEqual(result[pk1].shared_field, NORMAL[1].shared_field)
            self.assertEqual(result[pk1].translated_field, NORMAL[1].translated_field['en'])
            self.assertEqual(result[pk1].language_code, 'en')
            self.assertEqual(result[pk2].shared_field, NORMAL[2].shared_field)
            self.assertEqual(result[pk2].translated_field, NORMAL[2].translated_field['en'])
            self.assertEqual(result[pk2].language_code, 'en')


class FallbackNotImplementedTests(HvadTestCase):
    def test_defer(self):
        baseqs = Normal.objects.untranslated()
        self.assertRaises(NotImplementedError, baseqs.defer, 'shared_field')
        self.assertRaises(NotImplementedError, baseqs.only)
        self.assertRaises(NotImplementedError, baseqs.aggregate)
        self.assertRaises(NotImplementedError, baseqs.annotate)
