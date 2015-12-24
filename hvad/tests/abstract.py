from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import ConcreteAB, ConcreteABProxy
from hvad.test_utils.fixtures import ConcreteABFixture
from hvad.test_utils.data import NORMAL, CONCRETEAB
from django.utils import translation

class AbstractTests(HvadTestCase, ConcreteABFixture):
    normal_count = 2
    concreteab_count = 2

    def test_filter_and_iter(self):
        with translation.override('en'):
            with self.assertNumQueries(1):
                qs = (ConcreteAB.objects.language()
                                        .filter(shared_field_a__startswith='Shared')
                                        .order_by('shared_field_a'))
                self.assertEqual(len(qs), 2)
            with self.assertNumQueries(0):
                self.assertEqual([obj.shared_field_b_id for obj in qs],
                                 [self.normal_id[CONCRETEAB[1].shared_field_b],
                                  self.normal_id[CONCRETEAB[2].shared_field_b]])
                self.assertEqual([obj.shared_field_ab for obj in qs],
                                 [CONCRETEAB[1].shared_field_ab,
                                  CONCRETEAB[2].shared_field_ab])
                self.assertEqual([obj.translated_field_b for obj in qs],
                                 [CONCRETEAB[1].translated_field_b['en'],
                                  CONCRETEAB[2].translated_field_b['en']])
                self.assertEqual([obj.translated_field_ab for obj in qs],
                                 [CONCRETEAB[1].translated_field_ab['en'],
                                  CONCRETEAB[2].translated_field_ab['en']])
            with self.assertNumQueries(2): # this was not prefetched
                self.assertEqual([obj.translated_field_a.pk for obj in qs],
                                 [self.normal_id[CONCRETEAB[1].translated_field_a['en']],
                                  self.normal_id[CONCRETEAB[2].translated_field_a['en']]])

        qs = qs.all()   # discard cached results
        with translation.override('ja'):
            with self.assertNumQueries(1):
                self.assertEqual(len(qs), 2)
            with self.assertNumQueries(0):
                self.assertEqual([obj.translated_field_b for obj in qs],
                                 [CONCRETEAB[1].translated_field_b['ja'],
                                  CONCRETEAB[2].translated_field_b['ja']])
                self.assertEqual([obj.translated_field_ab for obj in qs],
                                 [CONCRETEAB[1].translated_field_ab['ja'],
                                  CONCRETEAB[2].translated_field_ab['ja']])
            with self.assertNumQueries(2): # this was not prefetched
                self.assertEqual([obj.translated_field_a.pk for obj in qs],
                                 [self.normal_id[CONCRETEAB[1].translated_field_a['ja']],
                                  self.normal_id[CONCRETEAB[2].translated_field_a['ja']]])

    def test_select_related(self):
        with translation.override('en'):
            qs = (ConcreteAB.objects.language()
                                    .select_related('shared_field_b', 'translated_field_a')
                                    .filter(shared_field_ab=CONCRETEAB[2].shared_field_ab))
            # does it work?
            with self.assertNumQueries(1):
                self.assertEqual(qs.count(), 1)
            with self.assertNumQueries(1):
                self.assertEqual(len(qs), 1)
                obj = qs[0]
            # does it actually cache stuff?
            with self.assertNumQueries(0):
                self.assertEqual(obj.shared_field_b.translated_field,
                                 NORMAL[CONCRETEAB[2].shared_field_b].translated_field['en'])
                self.assertEqual(obj.translated_field_a.translated_field,
                                 NORMAL[CONCRETEAB[2].translated_field_a['en']].translated_field['en'])

    def test_proxy(self):
        obj = (ConcreteABProxy.objects.language('en')
                                      .get(shared_field_a=CONCRETEAB[1].shared_field_a))
        self.assertTrue(isinstance(obj, ConcreteABProxy))
        self.assertTrue(str(obj).startswith('proxied'))
