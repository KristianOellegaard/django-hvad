# -*- coding: utf-8 -*-
from django.core.exceptions import FieldError
from django.db.models.query_utils import Q
from nani.exceptions import WrongManager
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import SingleNormalTestCase, NaniTestCase
from nani.utils import get_translation_aware_manager
from testproject.app.models import Normal, Related, Standard, Other


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

    def test_num_queries(self):
        with LanguageOverride('en'):
            en = Normal.objects.language('en').get(pk=1)
            with self.assertNumQueries(1):
                related = Standard.objects.select_related('normal').get(pk=1)
                self.assertEqual(related.normal.pk, en.pk)
            with self.assertNumQueries(0):
                self.assertEqual(related.normal.shared_field, en.shared_field)
            with self.assertNumQueries(1):
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
    
    def test_lookup_by_non_existing_field(self):
        en = Normal.objects.language('en').get(pk=1)
        with LanguageOverride('en'):
            self.assertRaises(FieldError, Standard.objects.get,
                              normal__non_existing_field=1)
        

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


class TripleRelationTests(NaniTestCase):
    def test_triple(self):
        normal = Normal.objects.language('en').create(shared_field='SHARED', translated_field='English')
        other = Other.objects.create(normal=normal)
        standard = Standard.objects.create(normal=normal, normal_field='NORMAL FIELD')

        obj = Normal.objects.language('en').get(standards__pk=standard.pk)
        self.assertEqual(obj.pk, normal.pk)

        obj = Normal.objects.language('en').get(others__pk=other.pk)
        self.assertEqual(obj.pk, normal.pk)

        # We created an english Normal object, so we want to make sure that we use 'en'
        with LanguageOverride('en'):
            obj = get_translation_aware_manager(Standard).get(normal__others__pk=other.pk)
            self.assertEqual(obj.pk, standard.pk)

        # If we don't use language 'en', it should give DoesNotExist, when using the
        # translation aware manager
        with LanguageOverride('ja'):
            manager = get_translation_aware_manager(Standard)
            self.assertRaises(Standard.DoesNotExist, manager.get, normal__others__pk=other.pk)

        # However, if we don't use the translation aware manager, we can query any
        # the shared fields in any language, and it should return the object,
        # even though there is no translated Normal objects
        with LanguageOverride('ja'):
            obj = Standard.objects.get(normal__others__pk=other.pk)
            self.assertEqual(obj.pk, standard.pk)