# -*- coding: utf-8 -*-
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import (Normal, ConcreteAB, ConcreteABProxy)
from hvad.test_utils.fixtures import TwoTranslatedConcreteABMixin
from hvad.test_utils.data import DOUBLE_NORMAL

class AbstractTests(HvadTestCase, TwoTranslatedConcreteABMixin):
    def setUp(self):
        super(AbstractTests, self).setUp()
        self.normal1 = Normal.objects.language('en').get(shared_field=DOUBLE_NORMAL[1]['shared_field'])
        self.normal2 = Normal.objects.language('en').get(shared_field=DOUBLE_NORMAL[2]['shared_field'])

    def test_filter_and_iter(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                qs = (ConcreteAB.objects.language()
                                        .filter(shared_field_a__startswith='Shared')
                                        .order_by('shared_field_a'))
                self.assertEqual(len(qs), 2)
            with self.assertNumQueries(0):
                self.assertEqual([obj.shared_field_b_id for obj in qs],
                                 [self.normal1.pk, self.normal2.pk])
                self.assertEqual([obj.shared_field_ab for obj in qs],
                                 [DOUBLE_NORMAL[1]['shared_field'], DOUBLE_NORMAL[2]['shared_field']])
                self.assertEqual([obj.translated_field_b for obj in qs],
                                 [DOUBLE_NORMAL[1]['translated_field_en'],
                                  DOUBLE_NORMAL[2]['translated_field_en']])
                self.assertEqual([obj.translated_field_ab for obj in qs],
                                 [DOUBLE_NORMAL[1]['translated_field_en'],
                                  DOUBLE_NORMAL[2]['translated_field_en']])
            with self.assertNumQueries(2): # this was not prefetched
                self.assertEqual([obj.translated_field_a.pk for obj in qs],
                                 [self.normal1.pk, self.normal1.pk])

        qs = qs.all()   # discard cached results
        with LanguageOverride('ja'):
            with self.assertNumQueries(1):
                self.assertEqual(len(qs), 2)
            with self.assertNumQueries(0):
                self.assertEqual([obj.translated_field_b for obj in qs],
                                 [DOUBLE_NORMAL[1]['translated_field_ja'],
                                  DOUBLE_NORMAL[2]['translated_field_ja']])
                self.assertEqual([obj.translated_field_ab for obj in qs],
                                 [DOUBLE_NORMAL[1]['translated_field_ja'],
                                  DOUBLE_NORMAL[2]['translated_field_ja']])
            with self.assertNumQueries(2): # this was not prefetched
                self.assertEqual([obj.translated_field_a.pk for obj in qs],
                                 [self.normal2.pk, self.normal2.pk])

    def test_select_related(self):
        with LanguageOverride('en'):
            qs = (ConcreteAB.objects.language()
                                    .select_related('shared_field_b', 'translated_field_a')
                                    .filter(shared_field_ab=DOUBLE_NORMAL[2]['shared_field']))
            # does it work?
            with self.assertNumQueries(1):
                self.assertEqual(qs.count(), 1)
            with self.assertNumQueries(1):
                self.assertEqual(len(qs), 1)
                obj = qs[0]
            # does it actually cache stuff?
            with self.assertNumQueries(0):
                self.assertEqual(obj.shared_field_b.translated_field, DOUBLE_NORMAL[2]['translated_field_en'])
                self.assertEqual(obj.translated_field_a.translated_field, DOUBLE_NORMAL[1]['translated_field_en'])

    def test_proxy(self):
        obj = (ConcreteABProxy.objects.language('en')
                                      .get(shared_field_a=DOUBLE_NORMAL[1]['shared_field']))
        self.assertTrue(isinstance(obj, ConcreteABProxy))
        self.assertTrue(str(obj).startswith('proxied'))
