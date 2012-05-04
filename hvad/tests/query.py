# -*- coding: utf-8 -*-
from django.db.models.query_utils import Q
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.data import DOUBLE_NORMAL
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal, AggregateModel
from hvad.test_utils.fixtures import TwoTranslatedNormalMixin


class FilterTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_simple_filter(self):
        qs = Normal.objects.language('en').filter(shared_field__contains='2')
        self.assertEqual(qs.count(), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[2]['shared_field'])
        self.assertEqual(obj.translated_field, DOUBLE_NORMAL[2]['translated_field_en'])
        qs = Normal.objects.language('ja').filter(shared_field__contains='1')
        self.assertEqual(qs.count(), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
        self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])
        
    def test_translated_filter(self):
        qs = Normal.objects.language('en').filter(translated_field__contains='English')
        self.assertEqual(qs.count(), 2)
        obj1, obj2 = qs
        self.assertEqual(obj1.shared_field, DOUBLE_NORMAL[1]['shared_field'])
        self.assertEqual(obj1.translated_field, DOUBLE_NORMAL[1]['translated_field_en'])
        self.assertEqual(obj2.shared_field, DOUBLE_NORMAL[2]['shared_field'])
        self.assertEqual(obj2.translated_field, DOUBLE_NORMAL[2]['translated_field_en'])


class IterTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_simple_iter(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                index = 0
                for obj in Normal.objects.language():
                    index += 1
                    self.assertEqual(obj.shared_field, DOUBLE_NORMAL[index]['shared_field'])
                    self.assertEqual(obj.translated_field, DOUBLE_NORMAL[index]['translated_field_en'])
        with LanguageOverride('ja'):
            with self.assertNumQueries(1):
                index = 0
                for obj in Normal.objects.language():
                    index += 1
                    self.assertEqual(obj.shared_field, DOUBLE_NORMAL[index]['shared_field'])
                    self.assertEqual(obj.translated_field, DOUBLE_NORMAL[index]['translated_field_ja'])
    def test_iter_unique_reply(self):
        # Make sure .all() only returns unique rows
        with LanguageOverride('en'):
            self.assertEqual(len(Normal.objects.all()), len(Normal.objects.untranslated()))

class UpdateTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_update_shared(self):
        NEW_SHARED = 'new shared'
        n1 = Normal.objects.language('en').get(pk=1)
        n2 = Normal.objects.language('en').get(pk=2)
        ja1 = Normal.objects.language('ja').get(pk=1)
        ja2 = Normal.objects.language('ja').get(pk=2)
        with self.assertNumQueries(1):
            Normal.objects.language('en').update(shared_field=NEW_SHARED)
        new1 = Normal.objects.language('en').get(pk=1)
        new2 = Normal.objects.language('en').get(pk=2)
        self.assertEqual(new1.shared_field, NEW_SHARED)
        self.assertEqual(new1.translated_field, n1.translated_field)
        self.assertEqual(new2.shared_field, NEW_SHARED)
        self.assertEqual(new2.translated_field, n2.translated_field)
        newja1 = Normal.objects.language('ja').get(pk=1)
        newja2 = Normal.objects.language('ja').get(pk=2)
        self.assertEqual(newja1.shared_field, NEW_SHARED)
        self.assertEqual(newja2.shared_field, NEW_SHARED)
        self.assertEqual(newja1.translated_field, ja1.translated_field)
        self.assertEqual(newja2.translated_field, ja2.translated_field)
        
    def test_update_translated(self):
        NEW_TRANSLATED = 'new translated'
        n1 = Normal.objects.language('en').get(pk=1)
        n2 = Normal.objects.language('en').get(pk=2)
        ja1 = Normal.objects.language('ja').get(pk=1)
        ja2 = Normal.objects.language('ja').get(pk=2)
        with self.assertNumQueries(1):
            Normal.objects.language('en').update(translated_field=NEW_TRANSLATED)
        new1 = Normal.objects.language('en').get(pk=1)
        new2 = Normal.objects.language('en').get(pk=2)
        self.assertEqual(new1.shared_field, n1.shared_field)
        self.assertEqual(new2.shared_field, n2.shared_field)
        self.assertEqual(new1.translated_field, NEW_TRANSLATED)
        self.assertEqual(new2.translated_field, NEW_TRANSLATED)
        # check it didn't touch japanese
        newja1 = Normal.objects.language('ja').get(pk=1)
        newja2 = Normal.objects.language('ja').get(pk=2)
        self.assertEqual(newja1.shared_field, ja1.shared_field)
        self.assertEqual(newja2.shared_field, ja2.shared_field)
        self.assertEqual(newja1.translated_field, ja1.translated_field)
        self.assertEqual(newja2.translated_field, ja2.translated_field)
        
    def test_update_mixed(self):
        NEW_SHARED = 'new shared'
        NEW_TRANSLATED = 'new translated'
        ja1 = Normal.objects.language('ja').get(pk=1)
        ja2 = Normal.objects.language('ja').get(pk=2)
        with self.assertNumQueries(2):
            Normal.objects.language('en').update(shared_field=NEW_SHARED, translated_field=NEW_TRANSLATED)
        new1 = Normal.objects.language('en').get(pk=1)
        new2 = Normal.objects.language('en').get(pk=2)
        self.assertEqual(new1.shared_field, NEW_SHARED)
        self.assertEqual(new1.translated_field, NEW_TRANSLATED)
        self.assertEqual(new2.shared_field, NEW_SHARED)
        self.assertEqual(new2.translated_field, NEW_TRANSLATED)
        newja1 = Normal.objects.language('ja').get(pk=1)
        newja2 = Normal.objects.language('ja').get(pk=2)
        self.assertEqual(newja1.shared_field, NEW_SHARED)
        self.assertEqual(newja2.shared_field, NEW_SHARED)
        # check it didn't touch japanese translated fields
        self.assertEqual(newja1.translated_field, ja1.translated_field)
        self.assertEqual(newja2.translated_field, ja2.translated_field)
        

class ValuesListTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_values_list_translated(self):
        values = Normal.objects.language('en').values_list('translated_field', flat=True)
        values_list = list(values)
        self.assertEqual(values_list, [DOUBLE_NORMAL[1]['translated_field_en'], DOUBLE_NORMAL[2]['translated_field_en']])
        
    def test_values_list_shared(self):
        values = Normal.objects.language('en').values_list('shared_field', flat=True)
        values_list = list(values)
        self.assertEqual(values_list, [DOUBLE_NORMAL[1]['shared_field'], DOUBLE_NORMAL[2]['shared_field']])
    
    def test_values_list_mixed(self):
        values = Normal.objects.language('en').values_list('shared_field', 'translated_field')
        values_list = list(values)
        check = [
            (DOUBLE_NORMAL[1]['shared_field'], DOUBLE_NORMAL[1]['translated_field_en']),
            (DOUBLE_NORMAL[2]['shared_field'], DOUBLE_NORMAL[2]['translated_field_en']),
        ]
        self.assertEqual(values_list, check)
        

class ValuesTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_values_shared(self):
        values = Normal.objects.language('en').values('shared_field')
        values_list = list(values)
        check = [
            {'shared_field': DOUBLE_NORMAL[1]['shared_field']},
            {'shared_field': DOUBLE_NORMAL[2]['shared_field']},
        ]
        self.assertEqual(values_list, check)
    
    def test_values_translated(self):
        values = Normal.objects.language('en').values('translated_field')
        values_list = list(values)
        check = [
            {'translated_field': DOUBLE_NORMAL[1]['translated_field_en']},
            {'translated_field': DOUBLE_NORMAL[2]['translated_field_en']},
        ]
        self.assertEqual(values_list, check)
        
    def test_values_mixed(self):
        values = Normal.objects.language('en').values('translated_field', 'shared_field')
        values_list = list(values)
        check = [
            {'translated_field': DOUBLE_NORMAL[1]['translated_field_en'],
             'shared_field': DOUBLE_NORMAL[1]['shared_field']},
            {'translated_field': DOUBLE_NORMAL[2]['translated_field_en'],
             'shared_field': DOUBLE_NORMAL[2]['shared_field']},
        ]
        self.assertEqual(values_list, check)
        
    def test_values_post_language(self):
        values = Normal.objects.using_translations().values('shared_field').language('en')
        values_list = list(values)
        check = [
            {'shared_field': DOUBLE_NORMAL[1]['shared_field']},
            {'shared_field': DOUBLE_NORMAL[2]['shared_field']},
        ]
        self.assertEqual(values_list, check)
        
    def test_values_post_filter(self):
        qs = Normal.objects.language('en').values('shared_field')
        values = qs.filter(shared_field=DOUBLE_NORMAL[1]['shared_field'])
        values_list = list(values)
        check = [
            {'shared_field': DOUBLE_NORMAL[1]['shared_field']},
        ]
        self.assertEqual(values_list, check)
        

class DeleteTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_delete_all(self):
        Normal.objects.all().delete()
        self.assertEqual(Normal.objects.count(), 0)
        self.assertEqual(Normal.objects._real_manager.count(), 0)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 0)
        
    def test_delete_translation(self):
        self.assertEqual(Normal._meta.translations_model.objects.count(), 4)
        Normal.objects.language('en').delete_translations()
        self.assertEqual(Normal.objects.untranslated().count(), 2)
        self.assertEqual(Normal.objects._real_manager.count(), 2)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        Normal.objects.language('ja').delete_translations()
        self.assertEqual(Normal.objects.untranslated().count(), 2)
        self.assertEqual(Normal.objects._real_manager.count(), 2)
        self.assertEqual(Normal._meta.translations_model.objects.count(), 0)


class GetTranslationFromInstanceTests(NaniTestCase):
    def test_simple(self):
        # Create the instances
        SHARED = 'shared'
        TRANS_EN = 'English'
        TRANS_JA = u'日本語'
        en = Normal.objects.language('en').create(
            shared_field=SHARED,
            translated_field=TRANS_EN,
        )
        ja = en
        ja.translate('ja')
        ja.translated_field = TRANS_JA
        ja.save()
        
        # get the english instance
        en = Normal.objects.language('en').get()
        
        # get the japanese *translations*
        ja_trans = en.translations.get_language('ja')
        
        # get the japanese *combined*
        
        ja = Normal.objects.language('ja').get(pk=en.pk)
        
        self.assertEqual(en.shared_field, SHARED)
        self.assertEqual(en.translated_field, TRANS_EN)
        self.assertRaises(AttributeError, getattr, ja_trans, 'shared_field')
        self.assertEqual(ja_trans.translated_field, TRANS_JA)
        self.assertEqual(ja.shared_field, SHARED)
        self.assertEqual(ja.translated_field, TRANS_JA)


class AggregateTests(NaniTestCase):
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


class NotImplementedTests(NaniTestCase):
    def test_defer(self):
        SHARED = 'shared'
        TRANS_EN = 'English'
        en = Normal.objects.language('en').create(
            shared_field=SHARED,
            translated_field=TRANS_EN,
        )
        
        baseqs = Normal.objects.language('en')
        
        self.assertRaises(NotImplementedError, baseqs.defer, 'shared_field')
        self.assertRaises(NotImplementedError, baseqs.in_bulk, [1,2,3,4])
        self.assertRaises(NotImplementedError, baseqs.annotate)
        self.assertRaises(NotImplementedError, baseqs.only)


class ExcludeTests(NaniTestCase):
    def test_defer(self):
        SHARED = 'shared'
        TRANS_EN = 'English'
        TRANS_JA = u'日本語'
        en = Normal.objects.language('en').create(
            shared_field=SHARED,
            translated_field=TRANS_EN,
        )
        ja = en
        ja.translate('ja')
        ja.translated_field = TRANS_JA
        ja.save()

        qs = Normal.objects.language('en').exclude(translated_field=TRANS_EN)
        self.assertEqual(qs.count(), 0)


class ComplexFilterTests(NaniTestCase):
    def test_defer(self):
        SHARED = 'shared'
        TRANS_EN = 'English'
        TRANS_JA = u'日本語'
        en = Normal.objects.language('en').create(
            shared_field=SHARED,
            translated_field=TRANS_EN,
        )
        ja = en
        ja.translate('ja')
        ja.translated_field = TRANS_JA
        ja.save()

        qs = Normal.objects.language('en').complex_filter({})
        self.assertEqual(qs.count(), 1)
        self.assertRaises(NotImplementedError, Normal.objects.language('en').complex_filter, Q(shared_field=SHARED))
    