from django.db import connection
from django.db.models import Count
from django.db.models.query_utils import Q
from django.utils import translation
from hvad.utils import get_cached_translation
from hvad.test_utils.data import NORMAL, STANDARD
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, AggregateModel, Standard, SimpleRelated
from hvad.test_utils.fixtures import NormalFixture, StandardFixture

class FilterTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_simple_filter(self):
        qs = Normal.objects.language('en').filter(shared_field__contains='2')
        self.assertEqual(qs.count(), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, NORMAL[2].shared_field)
        self.assertEqual(obj.translated_field, NORMAL[2].translated_field['en'])
        qs = Normal.objects.language('ja').filter(shared_field__contains='1')
        self.assertEqual(qs.count(), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])

    def test_translated_filter(self):
        qs = Normal.objects.language('en').filter(translated_field__contains='English')
        self.assertEqual(qs.count(), self.normal_count)
        obj1, obj2 = qs
        self.assertEqual(obj1.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj1.translated_field, NORMAL[1].translated_field['en'])
        self.assertEqual(obj2.shared_field, NORMAL[2].shared_field)
        self.assertEqual(obj2.translated_field, NORMAL[2].translated_field['en'])

    def test_fallbacks_filter(self):
        (Normal.objects.language('en')
                    .filter(shared_field=NORMAL[1].shared_field)
                    .delete_translations())
        with translation.override('en'):
            qs = Normal.objects.language().fallbacks()
            with self.assertNumQueries(2):
                self.assertEqual(qs.count(), self.normal_count)
                self.assertEqual(len(qs), self.normal_count)
            with self.assertNumQueries(0):
                self.assertCountEqual((obj.pk for obj in qs), tuple(self.normal_id.values()))
                self.assertCountEqual((obj.language_code for obj in qs), self.translations)

    def test_all_languages_filter(self):
        with self.assertNumQueries(2):
            qs = Normal.objects.language('all').filter(shared_field__contains='Shared')
            self.assertEqual(qs.count(), self.normal_count * len(self.translations))
            self.assertCountEqual((obj.shared_field for obj in qs),
                                  (NORMAL[1].shared_field,
                                   NORMAL[2].shared_field) * 2)
            self.assertCountEqual((obj.translated_field for obj in qs),
                                  (NORMAL[1].translated_field['en'],
                                   NORMAL[1].translated_field['ja'],
                                   NORMAL[2].translated_field['en'],
                                   NORMAL[2].translated_field['ja']))

        with self.assertNumQueries(2):
            qs = Normal.objects.language('all').filter(translated_field__contains='English')
            self.assertEqual(qs.count(), self.normal_count)
            self.assertCountEqual((obj.shared_field for obj in qs),
                                  (NORMAL[1].shared_field,
                                   NORMAL[2].shared_field))
            self.assertCountEqual((obj.translated_field for obj in qs),
                                  (NORMAL[1].translated_field['en'],
                                   NORMAL[2].translated_field['en']))

        with self.assertNumQueries(2):
            qs = Normal.objects.language('all').filter(translated_field__contains='1')
            self.assertEqual(qs.count(), 1)
            obj = qs[0]
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])

    def test_deferred_language_filter(self):
        with translation.override('ja'):
            qs = Normal.objects.language().filter(translated_field__contains='English')
        with translation.override('en'):
            self.assertEqual(qs.count(), self.normal_count)
            obj1, obj2 = qs
            self.assertEqual(obj1.shared_field, NORMAL[1].shared_field)
            self.assertEqual(obj1.translated_field, NORMAL[1].translated_field['en'])
            self.assertEqual(obj2.shared_field, NORMAL[2].shared_field)
            self.assertEqual(obj2.translated_field, NORMAL[2].translated_field['en'])


class ExtraTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_simple_extra(self):
        qs = Normal.objects.language('en').extra(select={'test_extra': '2 + 2'})
        self.assertEqual(qs.count(), self.normal_count)
        self.assertEqual(int(qs[0].test_extra), 4)


class QueryCachingTests(HvadTestCase, NormalFixture):
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
        with translation.override('en'):
            index = 0
            qs = Normal.objects.language().filter(pk=self.normal_id[1])
            for obj in qs:
                index += 1
            self.assertEqual(index, 1)
            self._try_all_cache_using_methods(qs, 1)

    def test_pickling_caches(self):
        import pickle
        with translation.override('en'):
            qs = Normal.objects.language().filter(pk=self.normal_id[1])
            pickle.dumps(qs)
            self._try_all_cache_using_methods(qs, 1)

    def test_len_caches(self):
        with translation.override('en'):
            qs = Normal.objects.language().filter(pk=self.normal_id[1])
            self.assertEqual(len(qs), 1)
            self._try_all_cache_using_methods(qs, 1)

    def test_bool_caches(self):
        with translation.override('en'):
            qs = Normal.objects.language().filter(pk=self.normal_id[1])
            self.assertTrue(qs)
            self._try_all_cache_using_methods(qs, 1)


class IterTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_simple_iter(self):
        with translation.override('en'):
            with self.assertNumQueries(1):
                for index, obj in enumerate(Normal.objects.language(), 1):
                    self.assertEqual(obj.shared_field, NORMAL[index].shared_field)
                    self.assertEqual(obj.translated_field, NORMAL[index].translated_field['en'])
        with translation.override('ja'):
            with self.assertNumQueries(1):
                for index, obj in enumerate(Normal.objects.language(), 1):
                    self.assertEqual(obj.shared_field, NORMAL[index].shared_field)
                    self.assertEqual(obj.translated_field, NORMAL[index].translated_field['ja'])

    def test_iter_unique_reply(self):
        # Make sure .all() only returns unique rows
        with translation.override('en'):
            self.assertEqual(len(Normal.objects.all()), len(Normal.objects.untranslated()))

    def test_iter_deferred_language(self):
        with translation.override('en'):
            qs = Normal.objects.language()
        with translation.override('ja'):
            for index, obj in enumerate(qs, 1):
                self.assertEqual(obj.shared_field, NORMAL[index].shared_field)
                self.assertEqual(obj.translated_field, NORMAL[index].translated_field['ja'])


class UpdateTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_update_shared(self):
        NEW_SHARED = 'new shared'
        n1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        n2 = Normal.objects.language('en').get(pk=self.normal_id[2])
        ja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        ja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        with self.assertNumQueries(1 if connection.features.update_can_self_select else 2):
            Normal.objects.language('en').update(shared_field=NEW_SHARED)
        new1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        new2 = Normal.objects.language('en').get(pk=self.normal_id[2])
        self.assertEqual(new1.shared_field, NEW_SHARED)
        self.assertEqual(new1.translated_field, n1.translated_field)
        self.assertEqual(new2.shared_field, NEW_SHARED)
        self.assertEqual(new2.translated_field, n2.translated_field)
        newja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        newja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        self.assertEqual(newja1.shared_field, NEW_SHARED)
        self.assertEqual(newja2.shared_field, NEW_SHARED)
        self.assertEqual(newja1.translated_field, ja1.translated_field)
        self.assertEqual(newja2.translated_field, ja2.translated_field)

    def test_update_translated(self):
        NEW_TRANSLATED = 'new translated'
        n1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        n2 = Normal.objects.language('en').get(pk=self.normal_id[2])
        ja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        ja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        with self.assertNumQueries(1):
            Normal.objects.language('en').update(translated_field=NEW_TRANSLATED)
        new1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        new2 = Normal.objects.language('en').get(pk=self.normal_id[2])
        self.assertEqual(new1.shared_field, n1.shared_field)
        self.assertEqual(new2.shared_field, n2.shared_field)
        self.assertEqual(new1.translated_field, NEW_TRANSLATED)
        self.assertEqual(new2.translated_field, NEW_TRANSLATED)
        # check it didn't touch japanese
        newja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        newja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        self.assertEqual(newja1.shared_field, ja1.shared_field)
        self.assertEqual(newja2.shared_field, ja2.shared_field)
        self.assertEqual(newja1.translated_field, ja1.translated_field)
        self.assertEqual(newja2.translated_field, ja2.translated_field)
        
    def test_update_mixed(self):
        NEW_SHARED = 'new shared'
        NEW_TRANSLATED = 'new translated'
        ja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        ja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        with self.assertNumQueries(2 if connection.features.update_can_self_select else 3):
            Normal.objects.language('en').update(
                shared_field=NEW_SHARED, translated_field=NEW_TRANSLATED
            )
        new1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        new2 = Normal.objects.language('en').get(pk=self.normal_id[2])
        self.assertEqual(new1.shared_field, NEW_SHARED)
        self.assertEqual(new1.translated_field, NEW_TRANSLATED)
        self.assertEqual(new2.shared_field, NEW_SHARED)
        self.assertEqual(new2.translated_field, NEW_TRANSLATED)
        newja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        newja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        self.assertEqual(newja1.shared_field, NEW_SHARED)
        self.assertEqual(newja2.shared_field, NEW_SHARED)
        # check it didn't touch japanese translated fields
        self.assertEqual(newja1.translated_field, ja1.translated_field)
        self.assertEqual(newja2.translated_field, ja2.translated_field)

    def test_update_deferred_language(self):
        NEW_TRANSLATED = 'new translated'
        n1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        n2 = Normal.objects.language('en').get(pk=self.normal_id[2])
        ja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        ja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        with translation.override('ja'):
            qs = Normal.objects.language()
        with translation.override('en'):
            with self.assertNumQueries(1):
                qs.update(translated_field=NEW_TRANSLATED)
        new1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        new2 = Normal.objects.language('en').get(pk=self.normal_id[2])
        self.assertEqual(new1.shared_field, n1.shared_field)
        self.assertEqual(new2.shared_field, n2.shared_field)
        self.assertEqual(new1.translated_field, NEW_TRANSLATED)
        self.assertEqual(new2.translated_field, NEW_TRANSLATED)
        # check it didn't touch japanese
        newja1 = Normal.objects.language('ja').get(pk=self.normal_id[1])
        newja2 = Normal.objects.language('ja').get(pk=self.normal_id[2])
        self.assertEqual(newja1.shared_field, ja1.shared_field)
        self.assertEqual(newja2.shared_field, ja2.shared_field)
        self.assertEqual(newja1.translated_field, ja1.translated_field)
        self.assertEqual(newja2.translated_field, ja2.translated_field)

    def test_update_fallbacks(self):
        # Test it works - note that is it still not recommended as the query is much
        # more complicated that it need to be
        qs = Normal.objects.language().fallbacks()
        with self.assertNumQueries(1 if connection.features.update_can_self_select else 2):
            qs.filter(shared_field=NORMAL[1].shared_field).update(shared_field='updated')

        self.assertEqual(Normal.objects.language('ja').get(shared_field='updated').pk, self.normal_id[1])
        self.assertEqual(Normal.objects.language('en').get(shared_field='updated').pk, self.normal_id[1])


class ValuesListTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_values_list_translated(self):
        values = Normal.objects.language('en').values_list('translated_field', flat=True)
        values_list = list(values)
        self.assertCountEqual(values_list, [NORMAL[1].translated_field['en'],
                                            NORMAL[2].translated_field['en']])

    def test_values_list_shared(self):
        values = Normal.objects.language('en').values_list('shared_field', flat=True)
        values_list = list(values)
        self.assertCountEqual(values_list, [NORMAL[1].shared_field,
                                            NORMAL[2].shared_field])
    
    def test_values_list_mixed(self):
        values = Normal.objects.language('en').values_list('shared_field', 'translated_field')
        values_list = list(values)
        check = [
            (NORMAL[1].shared_field, NORMAL[1].translated_field['en']),
            (NORMAL[2].shared_field, NORMAL[2].translated_field['en']),
        ]
        self.assertCountEqual(values_list, check)

    def test_values_list_deferred_language(self):
        with translation.override('ja'):
            qs = Normal.objects.language()
        with translation.override('en'):
            values = qs.values_list('shared_field', 'translated_field')
            values_list = list(values)
        check = [
            (NORMAL[1].shared_field, NORMAL[1].translated_field['en']),
            (NORMAL[2].shared_field, NORMAL[2].translated_field['en']),
        ]
        self.assertCountEqual(values_list, check)

    def test_values_list_language_all(self):
        values = (Normal.objects.language('all').filter(shared_field=NORMAL[1].shared_field)
                                                .values_list('shared_field', 'translated_field'))
        values_list = list(values)
        check = [
            (NORMAL[1].shared_field, NORMAL[1].translated_field['ja']),
            (NORMAL[1].shared_field, NORMAL[1].translated_field['en']),
        ]
        self.assertCountEqual(values_list, check)


class ValuesTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_values_shared(self):
        values = Normal.objects.language('en').values('shared_field')
        values_list = list(values)
        check = [
            {'shared_field': NORMAL[1].shared_field},
            {'shared_field': NORMAL[2].shared_field},
        ]
        self.assertCountEqual(values_list, check)

    def test_values_translated(self):
        values = Normal.objects.language('en').values('translated_field')
        values_list = list(values)
        check = [
            {'translated_field': NORMAL[1].translated_field['en']},
            {'translated_field': NORMAL[2].translated_field['en']},
        ]
        self.assertCountEqual(values_list, check)
        
    def test_values_mixed(self):
        values = Normal.objects.language('en').values('translated_field', 'shared_field')
        values_list = list(values)
        check = [
            {'translated_field': NORMAL[1].translated_field['en'],
             'shared_field': NORMAL[1].shared_field},
            {'translated_field': NORMAL[2].translated_field['en'],
             'shared_field': NORMAL[2].shared_field},
        ]
        self.assertCountEqual(values_list, check)
        
    def test_values_post_language(self):
        values = Normal.objects.language().values('shared_field').language('en')
        values_list = list(values)
        check = [
            {'shared_field': NORMAL[1].shared_field},
            {'shared_field': NORMAL[2].shared_field},
        ]
        self.assertCountEqual(values_list, check)
        
    def test_values_post_filter(self):
        qs = Normal.objects.language('en').values('shared_field')
        values = qs.filter(shared_field=NORMAL[1].shared_field)
        values_list = list(values)
        check = [
            {'shared_field': NORMAL[1].shared_field},
        ]
        self.assertCountEqual(values_list, check)

    def test_values_deferred_language(self):
        with translation.override('ja'):
            qs = Normal.objects.language()
        with translation.override('en'):
            values = qs.values('translated_field')
            values_list = list(values)
        check = [
            {'translated_field': NORMAL[1].translated_field['en']},
            {'translated_field': NORMAL[2].translated_field['en']},
        ]
        self.assertCountEqual(values_list, check)

    def test_values_language_all(self):
        values = (Normal.objects.language('all').filter(shared_field=NORMAL[1].shared_field)
                                                .values('shared_field', 'translated_field'))
        values_list = list(values)
        check = [
            {'shared_field': NORMAL[1].shared_field,
             'translated_field': NORMAL[1].translated_field['ja']},
            {'shared_field': NORMAL[1].shared_field,
             'translated_field': NORMAL[1].translated_field['en']},
        ]
        self.assertCountEqual(values_list, check)

class InBulkTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_empty_in_bulk(self):
        with self.assertNumQueries(0):
            result = Normal.objects.language('en').in_bulk([])
            self.assertEqual(len(result), 0)

    def test_in_bulk(self):
        pk1, pk2 = self.normal_id[1], self.normal_id[2]
        with self.assertNumQueries(1):
            result = Normal.objects.language('en').in_bulk([pk1, pk2])
            self.assertCountEqual((pk1, pk2), result)
        with self.assertNumQueries(0):
            self.assertEqual(result[pk1].shared_field, NORMAL[1].shared_field)
            self.assertEqual(result[pk1].translated_field, NORMAL[1].translated_field['en'])
            self.assertEqual(result[pk1].language_code, 'en')
            self.assertEqual(result[pk2].shared_field, NORMAL[2].shared_field)
            self.assertEqual(result[pk2].translated_field, NORMAL[2].translated_field['en'])
            self.assertEqual(result[pk2].language_code, 'en')

    def test_untranslated_in_bulk(self):
        pk1 = self.normal_id[1]
        with translation.override('ja'):
            with self.assertNumQueries(1):
                result = Normal.objects.untranslated().in_bulk([pk1])
                self.assertCountEqual((pk1,), result)
            with self.assertNumQueries(0):
                self.assertEqual(result[pk1].shared_field, NORMAL[1].shared_field)
            with self.assertNumQueries(1):
                self.assertEqual(result[pk1].translated_field, NORMAL[1].translated_field['ja'])
            with self.assertNumQueries(0):
                self.assertEqual(result[pk1].language_code, 'ja')

    def test_fallbacks_in_bulk(self):
        (Normal.objects.language('en')
                       .filter(shared_field=NORMAL[2].shared_field)
                       .delete_translations())
        with self.assertNumQueries(1):
            pk1, pk2 = self.normal_id[1], self.normal_id[2]
            result = Normal.objects.language('en').fallbacks('de', 'ja').in_bulk([pk1, pk2])
            self.assertCountEqual((pk1, pk2), result)
        with self.assertNumQueries(0):
            self.assertEqual(result[pk1].shared_field, NORMAL[1].shared_field)
            self.assertEqual(result[pk1].translated_field, NORMAL[1].translated_field['en'])
            self.assertEqual(result[pk1].language_code, 'en')
            self.assertEqual(result[pk2].shared_field, NORMAL[2].shared_field)
            self.assertEqual(result[pk2].translated_field, NORMAL[2].translated_field['ja'])
            self.assertEqual(result[pk2].language_code, 'ja')

    def test_all_languages_in_bulk(self):
        with self.assertRaises(ValueError):
            Normal.objects.language('all').in_bulk([self.normal_id[1]])

    def test_in_bulk_deferred_language(self):
        pk1 = self.normal_id[1]
        with translation.override('ja'):
            qs = Normal.objects.language()
        with translation.override('en'):
            result = qs.in_bulk([pk1])
            self.assertCountEqual((pk1,), result)
            self.assertEqual(result[pk1].shared_field, NORMAL[1].shared_field)
            self.assertEqual(result[pk1].translated_field, NORMAL[1].translated_field['en'])
            self.assertEqual(result[pk1].language_code, 'en')


class DeleteTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_delete_all(self):
        Normal.objects.all().delete()
        self.assertEqual(Normal.objects.count(), 0)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 0)

    def test_delete_translation(self):
        self.assertEqual(Normal._meta.translations_model.objects.count(), 4)
        Normal.objects.language('en').delete_translations()
        self.assertEqual(Normal.objects.untranslated().count(), 2)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        Normal.objects.language('ja').delete_translations()
        self.assertEqual(Normal.objects.untranslated().count(), 2)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 0)

    def test_filtered_delete_translation(self):
        self.assertEqual(Normal._meta.translations_model.objects.count(), 4)
        (Normal.objects.language('en')
                       .filter(shared_field=NORMAL[1].shared_field)
                       .delete_translations())
        self.assertEqual(Normal.objects.untranslated().count(), 2)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 3)
        (Normal.objects.language('ja')
                       .filter(translated_field=NORMAL[2].translated_field['ja'])
                       .delete_translations())
        self.assertEqual(Normal.objects.untranslated().count(), 2)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)

    def test_delete_translation_deferred_language(self):
        self.assertEqual(Normal._meta.translations_model.objects.count(), 4)
        with translation.override('ja'):
            qs = Normal.objects.language()
        with translation.override('en'):
            qs.delete_translations()

        self.assertEqual(Normal.objects.language('ja').count(), 2)
        self.assertEqual(Normal.objects.language('en').count(), 0)

    def test_delete_fallbacks(self):
        qs = Normal.objects.language().fallbacks()
        qs.filter(shared_field=NORMAL[1].shared_field).delete()

        self.assertEqual(Normal.objects.language('ja').count(), self.normal_count - 1)
        self.assertEqual(Normal.objects.language('en').count(), self.normal_count - 1)


class GetTranslationFromInstanceTests(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_simple(self):
        # get the english instance
        en = Normal.objects.language('en').get()

        # get the japanese *translations*
        ja_trans = en.translations.get_language('ja')

        # get the japanese *combined*
        ja = Normal.objects.language('ja').get(pk=en.pk)

        self.assertEqual(en.shared_field, NORMAL[1].shared_field)
        self.assertEqual(en.translated_field, NORMAL[1].translated_field['en'])
        self.assertRaises(AttributeError, getattr, ja_trans, 'shared_field')
        self.assertEqual(ja_trans.translated_field, NORMAL[1].translated_field['ja'])
        self.assertEqual(ja.shared_field, NORMAL[1].shared_field)
        self.assertEqual(ja.translated_field, NORMAL[1].translated_field['ja'])

    def test_cached_autoload(self):
        # get the english instance
        en = Normal.objects.untranslated().prefetch_related('translations').get()
        with self.assertNumQueries(0):
            ja_trans = en.translations.get_language('ja')

        # get the japanese *combined*
        ja = Normal.objects.language('ja').get(pk=en.pk)

        self.assertEqual(en.shared_field, NORMAL[1].shared_field)
        self.assertEqual(en.translated_field, NORMAL[1].translated_field['en'])
        self.assertRaises(AttributeError, getattr, ja_trans, 'shared_field')
        self.assertEqual(ja_trans.translated_field, NORMAL[1].translated_field['ja'])
        self.assertEqual(ja.shared_field, NORMAL[1].shared_field)
        self.assertEqual(ja.translated_field, NORMAL[1].translated_field['ja'])

    def test_cached_no_autoload(self):
        with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': False}):
            en = Normal.objects.untranslated().prefetch_related('translations').get()
            ja = Normal.objects.language('ja').get(pk=en.pk)

            self.assertEqual(en.shared_field, NORMAL[1].shared_field)
            self.assertRaises(AttributeError, getattr, en, 'translated_field') # no autoload => error
            self.assertEqual(ja.shared_field, NORMAL[1].shared_field)
            self.assertEqual(ja.translated_field, NORMAL[1].translated_field['ja'])

    def test_not_exist(self):
        # Without prefetching
        en = Normal.objects.untranslated().get()
        with self.assertRaises(Normal.DoesNotExist):
            en.translations.get_language('tt')
        # With prefetching
        en = Normal.objects.untranslated().prefetch_related('translations').get()
        with self.assertRaises(Normal.DoesNotExist):
            en.translations.get_language('tt')

class AggregateTests(HvadTestCase):
    def test_aggregate(self):
        from django.db.models import Avg

        # Initial data
        AggregateModel.objects.language("en").create(number=10, translated_number=20)
        AggregateModel.objects.language("en").create(number=0, translated_number=0)

        # Check both the translated and the shared aggregates as arguments
        self.assertEqual(AggregateModel.objects.language("en").aggregate(Avg("number")), {'number__avg': 5})
        self.assertEqual(AggregateModel.objects.language("en").aggregate(Avg("translated_number")), {'translated_number__avg': 10})

        # Check the same calculation, but with keyword arguments
        self.assertEqual(AggregateModel.objects.language("en").aggregate(num=Avg("number")), {'num': 5})
        self.assertEqual(AggregateModel.objects.language("en").aggregate(tnum=Avg("translated_number")), {'tnum': 10})

class AnnotateTests(HvadTestCase, StandardFixture, NormalFixture):
    normal_count = 2
    standard_count = 4

    def test_annotate(self):
        qs = Normal.objects.language('en').annotate(Count('standards'))
        self.assertEqual(len(qs), self.normal_count)
        self.assertEqual(qs[0].standards__count, 2)
        self.assertEqual(qs[1].standards__count, 2)

        qs = Normal.objects.language('en').annotate(foo=Count('standards'))
        self.assertEqual(len(qs), self.normal_count)
        self.assertEqual(qs[0].foo, 2)
        self.assertEqual(qs[1].foo, 2)

        with self.assertRaises(ValueError):
            qs = Normal.objects.language('en').annotate(Count('standards'), standards__count=Count('standards'))

    def test_annotate_filter(self):
        "Field translation ignores annotations"
        qs = (Normal.objects.language('en').annotate(annotation=Count('standards'))
                                           .filter(annotation=2))
        self.assertEqual(len(qs), self.normal_count)
        self.assertEqual(qs[0].annotation, 2)
        self.assertEqual(qs[1].annotation, 2)

class DeferOnlyTests(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_only_shared(self):
        with self.assertNumQueries(1):
            qs = list(Normal.objects.language('en').only('id'))
        obj = qs[0]
        self.assertNotIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])
        self.assertIn('translated_field', get_cached_translation(obj).__dict__)

    def test_only_translated(self):
        with self.assertNumQueries(1):
            qs = list(Normal.objects.language('en').only('language_code'))
        obj = qs[0]
        self.assertNotIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])
        self.assertIn('translated_field', get_cached_translation(obj).__dict__)

    def test_only_split(self):
        with self.assertNumQueries(1):
            qs = list(Normal.objects.language('en').only('shared_field', 'language_code'))
        obj = qs[0]
        self.assertIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])
        self.assertIn('translated_field', get_cached_translation(obj).__dict__)

    def test_defer_shared(self):
        with self.assertNumQueries(1):
            qs = list(Normal.objects.language('en').defer('shared_field'))
        obj = qs[0]
        self.assertNotIn('shared_field', obj.__dict__)
        self.assertIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertIn('shared_field', obj.__dict__)

    def test_defer_translated(self):
        with self.assertNumQueries(1):
            qs = list(Normal.objects.language('en').defer('translated_field'))
        obj = qs[0]
        self.assertIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])
        self.assertIn('translated_field', get_cached_translation(obj).__dict__)

    def test_defer_split(self):
        with self.assertNumQueries(1):
            qs = list(Normal.objects.language('en').defer('shared_field', 'translated_field'))
        obj = qs[0]
        self.assertNotIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertIn('shared_field', obj.__dict__)

        with self.assertNumQueries(1):
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])
        self.assertIn('translated_field', get_cached_translation(obj).__dict__)

    def test_defer_chained(self):
        """ Mutiple defer calls are cumulative, defer(None) resets everything """
        qs = Normal.objects.language('en').defer('shared_field').defer('translated_field')
        with self.assertNumQueries(1):
            obj = list(qs)[0]
        self.assertNotIn('shared_field', obj.__dict__)
        self.assertNotIn('translated_field', get_cached_translation(obj).__dict__)

        qs = qs.defer(None)
        with self.assertNumQueries(1):
            obj = list(qs)[0]
        self.assertIn('shared_field', obj.__dict__)
        self.assertIn('translated_field', get_cached_translation(obj).__dict__)


class NotImplementedTests(HvadTestCase):
    def test_notimplemented(self):
        baseqs = SimpleRelated.objects.language('en')
        
        self.assertRaises(NotImplementedError, baseqs.bulk_create, [])
        # select_related with no field is not implemented
        self.assertRaises(NotImplementedError, baseqs.select_related)
        self.assertRaises(NotImplementedError, baseqs.update_or_create)


class ExcludeTests(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_defer(self):
        qs = Normal.objects.language('en').exclude(translated_field=NORMAL[1].translated_field['en'])
        self.assertEqual(qs.count(), 0)

    def test_fallbacks_exclude(self):
        (Normal.objects.language('en')
                       .filter(shared_field=NORMAL[1].shared_field)
                       .delete_translations())
        qs = (Normal.objects.language('en')
                            .fallbacks('de', 'ja')
                            .exclude(shared_field=NORMAL[1].shared_field))
        self.assertEqual(qs.count(), 0)

    def test_all_languages_exclude(self):
        qs = Normal.objects.language('all').exclude(translated_field=NORMAL[1].translated_field['en'])
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].translated_field, NORMAL[1].translated_field['ja'])

    def test_invalid_all_languages_exclude(self):
        with self.assertRaises(ValueError):
            Normal.objects.language().exclude(language_code='all')


class ComplexFilterTests(HvadTestCase, StandardFixture, NormalFixture):
    normal_count = 2
    standard_count = 2

    def test_qobject_filter(self):
        shared_contains_one = Q(shared_field__contains='1')
        shared_contains_two = Q(shared_field__contains='2')

        qs = Normal.objects.language('en').filter(shared_contains_two)
        self.assertEqual(qs.count(), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, NORMAL[2].shared_field)
        self.assertEqual(obj.translated_field, NORMAL[2].translated_field['en'])

        qs = (Normal.objects.language('ja').filter(Q(shared_contains_one | shared_contains_two))
                                           .order_by('shared_field'))
        self.assertEqual(qs.count(), 2)
        obj = qs[0]
        self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])
        obj = qs[1]
        self.assertEqual(obj.shared_field, NORMAL[2].shared_field)
        self.assertEqual(obj.translated_field, NORMAL[2].translated_field['ja'])

    def test_aware_qobject_filter(self):
        from hvad.utils import get_translation_aware_manager
        manager = get_translation_aware_manager(Standard)

        normal_one = Q(normal_field=STANDARD[1].normal_field)
        normal_two = Q(normal_field=STANDARD[2].normal_field)
        shared_one = Q(normal__shared_field=NORMAL[STANDARD[1].normal].shared_field)
        translated_one_en = Q(normal__translated_field=NORMAL[STANDARD[1].normal].translated_field['en'])
        translated_two_en = Q(normal__translated_field=NORMAL[STANDARD[2].normal].translated_field['en'])

        # control group test
        with translation.override('en'):
            qs = manager.filter(shared_one)
            self.assertEqual(qs.count(), 1)
            obj = qs[0]
            self.assertEqual(obj.normal_field, STANDARD[1].normal_field)

            # basic Q object test
            qs = manager.filter(translated_one_en)
            self.assertEqual(qs.count(), 1)
            obj = qs[0]
            self.assertEqual(obj.normal_field, STANDARD[1].normal_field)

            # test various intersection combinations
            # use a spurious Q to test the logic of recursion along the way
            qs = manager.filter(Q(normal_one & shared_one & translated_one_en))
            self.assertEqual(qs.count(), 1)
            obj = qs[0]
            self.assertEqual(obj.normal_field, STANDARD[1].normal_field)

            qs = manager.filter(Q(normal_one & translated_two_en))
            self.assertEqual(qs.count(), 0)
            qs = manager.filter(Q(shared_one & translated_two_en))
            self.assertEqual(qs.count(), 0)
            qs = manager.filter(Q(translated_one_en & translated_two_en))
            self.assertEqual(qs.count(), 0)

            # test various union combinations
            qs = manager.filter(Q(normal_one | translated_one_en))
            self.assertEqual(qs.count(), 1)
            qs = manager.filter(Q(shared_one | translated_one_en))
            self.assertEqual(qs.count(), 1)

            qs = manager.filter(Q(normal_one | translated_two_en))
            self.assertEqual(qs.count(), 2)
            qs = manager.filter(Q(shared_one | translated_two_en))
            self.assertEqual(qs.count(), 2)

            qs = manager.filter(Q(translated_one_en | translated_two_en))
            self.assertEqual(qs.count(), 2)

            # misc more complex combinations
            qs = manager.filter(Q(normal_one & (translated_one_en | translated_two_en)))
            self.assertEqual(qs.count(), 1)
            qs = manager.filter(Q(normal_two & (translated_one_en | translated_two_en)))
            self.assertEqual(qs.count(), 1)
            qs = manager.filter(shared_one & ~translated_one_en)
            self.assertEqual(qs.count(), 0)
            qs = manager.filter(shared_one & ~translated_two_en)
            self.assertEqual(qs.count(), 1)

    def test_defer(self):
        qs = Normal.objects.language('en').complex_filter({})
        self.assertEqual(qs.count(), self.normal_count)
        self.assertRaises(NotImplementedError,
                          Normal.objects.language('en').complex_filter,
                          Q(shared_field=NORMAL[1].shared_field))
