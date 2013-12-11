# -*- coding: utf-8 -*-
from hvad.test_utils.data import DOUBLE_NORMAL
from hvad.test_utils.testcase import NaniTestCase
from hvad.test_utils.project.app.models import (Normal, CustomManagerProxy,
                                                Standard, CustomManagerStandardProxy)
from hvad.test_utils.fixtures import TwoTranslatedNormalMixin, TwoNormalOneStandardMixin


class CustomManagersTests(NaniTestCase, TwoTranslatedNormalMixin):
    def test_simple_filter(self):
        """ Tests that the custom queryset is working. Control group for next tests. """
        qs = CustomManagerProxy.objects.language('en').having_translated_field(
                DOUBLE_NORMAL[1]['translated_field_en'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
        self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_en'])
        qs = CustomManagerProxy.objects.language('ja').having_translated_field(
                DOUBLE_NORMAL[1]['translated_field_ja'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
        self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])

    def test_any_language_filter(self):
        qs = CustomManagerProxy.objects.any_language().having_translated_field(
                DOUBLE_NORMAL[1]['translated_field_en'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])

        qs = CustomManagerProxy.objects.any_language().having_translated_field(
                DOUBLE_NORMAL[1]['translated_field_ja'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])

        # Try setting an invalid aware queryset override and check it is detected
        from django.db.models.query import QuerySet
        CustomManagerProxy.objects.translation_aware_queryset_class = QuerySet
        self.assertRaises(TypeError, CustomManagerProxy.objects.any_language)
        del CustomManagerProxy.objects.translation_aware_queryset_class

    def test_translation_aware_custom_manager(self):
        from hvad.utils import get_translation_aware_custom_manager
        manager = get_translation_aware_custom_manager(CustomManagerProxy)
        qs = manager.having_translated_field(DOUBLE_NORMAL[1]['translated_field_en'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
        qs = manager.having_translated_field(DOUBLE_NORMAL[1]['translated_field_ja'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])

    def test_translation_aware_custom_queryset(self):
        from hvad.utils import get_translation_aware_custom_manager
        manager = get_translation_aware_custom_manager(CustomManagerProxy)
        qs = manager.all().having_translated_field(DOUBLE_NORMAL[1]['translated_field_en'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
        qs = manager.all().having_translated_field(DOUBLE_NORMAL[1]['translated_field_ja'])
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])

class CustomManagersRelationTests(NaniTestCase, TwoNormalOneStandardMixin):
    def test_standard_queryset(self):
        """ On models without a custom manager, we should have regular aware stuff"""
        en = Normal.objects.language('en').get(pk=1)

        # First test regular translation aware manager as a control test
        from hvad.utils import get_translation_aware_manager
        manager = get_translation_aware_manager(Standard)
        qs = manager.all().filter(normal__translated_field=en.translated_field)
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.normal.shared_field, en.shared_field)
        self.assertEqual(obj.normal.translated_field, en.translated_field)

        from hvad.utils import get_translation_aware_custom_manager
        manager = get_translation_aware_custom_manager(Standard)
        qs = manager.all().filter(normal__translated_field=en.translated_field)
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.normal.shared_field, en.shared_field)
        self.assertEqual(obj.normal.translated_field, en.translated_field)

    def test_standard_custom_queryset(self):
        """ Tests using a nontranslatable model """
        from hvad.utils import (get_translation_aware_manager,
                                get_translation_aware_custom_manager)
        en = Normal.objects.language('en').get(pk=1)

        manager = get_translation_aware_manager(CustomManagerStandardProxy)
        qs = manager.filter(normal__translated_field=en.translated_field)
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].normal.translated_field, en.translated_field)
        self.assertFalse(hasattr(qs, 'having_normal_translated_field'))

        manager = get_translation_aware_custom_manager(CustomManagerStandardProxy)
        qs = manager.filter(normal__translated_field=en.translated_field)
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].normal.translated_field, en.translated_field)
        self.assertTrue(hasattr(qs, 'having_normal_translated_field'))

        qs = manager.having_normal_translated_field(en.translated_field)
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.normal.shared_field, en.shared_field)
        self.assertEqual(obj.normal.translated_field, en.translated_field)

        qs = manager.all().having_normal_translated_field(en.translated_field)
        self.assertEqual(len(qs), 1)
        obj = qs[0]
        self.assertEqual(obj.normal.shared_field, en.shared_field)
        self.assertEqual(obj.normal.translated_field, en.translated_field)
