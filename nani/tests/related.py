# -*- coding: utf-8 -*-
from django.db.models.query_utils import Q
from nani.exceptions import WrongManager
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import SingleNormalTestCase, NaniTestCase
from nani.test_utils import unittest as ut2
from nani.utils import get_translation_aware_manager
from testproject.app.models import Normal, Related, Standard


class NormalToNormalFKTest(SingleNormalTestCase):
    def test_relation(self):
        """
        'normal' (aka 'shared') relations are relations from the shared (or
        normal) model to another shared (or normal) model.
        
        They should behave like normal foreign keys in Django
        """
        normal = self.get_obj()
        related = Related.objects.create(normal=normal)
        self.assertEqual(related.normal.pk, normal.pk)
        self.assertEqual(related.normal.shared_field, normal.shared_field)
        self.assertEqual(related.normal.translated_field, normal.translated_field)
        self.assertTrue(related in normal.rel1.all())


class NormalToTransFKTest(SingleNormalTestCase):
    @ut2.skip("TranslatedForeignKeys might never be implemented")
    def test_relation(self):
        """
        TranslatedForeignKeys are FKs linking to a specific translation.
        
        While they are used the same way as normal FKs, they internally change
        their target model to the translation model.
        """
        en = self.get_obj()
        ja = en
        ja.translate('ja')
        ja.translated_field = u'何'
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        related = Related.objects.language('en').create(normal_trans=ja)
        with LanguageOverride('en'):
            related = self.reload(related)
            self.assertEqual(related.normal_trans.pk, ja.pk)
            self.assertEqual(related.normal_trans.shared_field, ja.shared_field)
            self.assertEqual(related.normal_trans.translated_field, ja.translated_field)
            self.assertTrue(related in ja.rel2.all())


class TransToNormalFKTest(NaniTestCase):
    pass


class TransToTransFKTest(NaniTestCase):
    pass


class StandardToTransFKTest(NaniTestCase):
    fixtures = ['standard.json']
    
    def test_relation(self):
        en = Normal.objects.language('en').get(pk=1)
        ja = Normal.objects.language('ja').get(pk=1)
        related = Standard.objects.get(pk=1)
        with LanguageOverride('en'):
            related = self.reload(related)
            self.assertEqual(related.normal.pk, en.pk)
            self.assertEqual(related.normal.shared_field, en.shared_field)
            self.assertEqual(related.normal.translated_field, en.translated_field)
            self.assertTrue(related in en.standards.all())
        with LanguageOverride('ja'):
            related = self.reload(related)
            self.assertEqual(related.normal.pk, ja.pk)
            self.assertEqual(related.normal.shared_field, ja.shared_field)
            self.assertEqual(related.normal.translated_field, ja.translated_field)
            self.assertTrue(related in ja.standards.all())
    
    @ut2.skip("For now, having 2 queries and the correct result is more important than having 1 query")
    def test_num_queries(self):
        with LanguageOverride('en'):
            en = Normal.objects.language('en').get(pk=1)
            with self.assertNumQueries(1):
                related = Standard.objects.select_related('normal').get(pk=1)
                self.assertEqual(related.normal.pk, en.pk)
                self.assertEqual(related.normal.shared_field, en.shared_field)
                self.assertEqual(related.normal.translated_field, en.translated_field)

    def test_lookup_by_pk(self):
        en = Normal.objects.language('en').get(pk=1)
        by_pk = Standard.objects.get(normal__pk=en.pk)
        with LanguageOverride('en'):
            self.assertEqual(by_pk.normal.pk, en.pk)
            self.assertEqual(by_pk.normal.shared_field, en.shared_field)
            self.assertEqual(by_pk.normal.translated_field, en.translated_field)
            self.assertTrue(by_pk in en.standards.all())
            
    def test_lookup_by_shared_field(self):
        en = Normal.objects.language('en').get(pk=1)
        by_shared_field = Standard.objects.get(normal__shared_field=en.shared_field)
        with LanguageOverride('en'):
            self.assertEqual(by_shared_field.normal.pk, en.pk)
            self.assertEqual(by_shared_field.normal.shared_field, en.shared_field)
            self.assertEqual(by_shared_field.normal.translated_field, en.translated_field)
            self.assertTrue(by_shared_field in en.standards.all())
    
    def test_lookup_by_translated_field(self):
        en = Normal.objects.language('en').get(pk=1)
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            by_translated_field = translation_aware_manager.get(normal__translated_field=en.translated_field)
            self.assertEqual(by_translated_field.normal.pk, en.pk)
            self.assertEqual(by_translated_field.normal.shared_field, en.shared_field)
            self.assertEqual(by_translated_field.normal.translated_field, en.translated_field)
            self.assertTrue(by_translated_field in en.standards.all())
            
    def test_lookup_by_translated_field_requires_translation_aware_manager(self):
        en = Normal.objects.language('en').get(pk=1)
        with LanguageOverride('en'):
            self.assertRaises(WrongManager, Standard.objects.get,
                              normal__translated_field=en.translated_field)
    
    def test_lookup_by_translated_field_using_q_objects(self):
        en = Normal.objects.language('en').get(pk=1)
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            q = Q(normal__translated_field=en.translated_field)
            by_translated_field = translation_aware_manager.get(q)
            self.assertEqual(by_translated_field.normal.pk, en.pk)
            self.assertEqual(by_translated_field.normal.shared_field, en.shared_field)
            self.assertEqual(by_translated_field.normal.translated_field, en.translated_field)
            self.assertTrue(by_translated_field in en.standards.all())
            
    def test_filter_by_shared_field(self):
        en = Normal.objects.language('en').get(pk=1)
        with LanguageOverride('en'):
            by_shared_field = Standard.objects.filter(normal__shared_field=en.shared_field)
            normals = [obj.normal.pk for obj in by_shared_field]
            expected = [en.pk]
            self.assertEqual(normals, expected)
            shared_fields = [obj.normal.shared_field for obj in by_shared_field]
            expected_fields = [en.shared_field]
            self.assertEqual(shared_fields, expected_fields)
            translated_fields = [obj.normal.translated_field for obj in by_shared_field]
            expected_fields = [en.translated_field]
            self.assertEqual(translated_fields, expected_fields)
            for obj in by_shared_field:
                self.assertTrue(obj in en.standards.all())
    
    def test_filter_by_translated_field(self):
        en = Normal.objects.language('en').get(pk=1)
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            by_translated_field = translation_aware_manager.filter(normal__translated_field=en.translated_field)
            normals = [obj.normal.pk for obj in by_translated_field]
            expected = [en.pk]
            self.assertEqual(normals, expected)
            shared_fields = [obj.normal.shared_field for obj in by_translated_field]
            expected_fields = [en.shared_field]
            self.assertEqual(shared_fields, expected_fields)
            translated_fields = [obj.normal.translated_field for obj in by_translated_field]
            expected_fields = [en.translated_field]
            self.assertEqual(translated_fields, expected_fields)
            for obj in by_translated_field:
                self.assertTrue(obj in en.standards.all())
            
    def test_filter_by_translated_field_requires_translation_aware_manager(self):
        en = Normal.objects.language('en').get(pk=1)
        with LanguageOverride('en'):
            self.assertRaises(WrongManager, Standard.objects.filter,
                              normal__translated_field=en.translated_field)
    
    def test_filter_by_translated_field_using_q_objects(self):
        en = Normal.objects.language('en').get(pk=1)
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            q = Q(normal__translated_field=en.translated_field)
            by_translated_field = translation_aware_manager.filter(q)
            normals = [obj.normal.pk for obj in by_translated_field]
            expected = [en.pk]
            self.assertEqual(normals, expected)
            shared_fields = [obj.normal.shared_field for obj in by_translated_field]
            expected_fields = [en.shared_field]
            self.assertEqual(shared_fields, expected_fields)
            translated_fields = [obj.normal.translated_field for obj in by_translated_field]
            expected_fields = [en.translated_field]
            self.assertEqual(translated_fields, expected_fields)
            for obj in by_translated_field:
                self.assertTrue(obj in en.standards.all())