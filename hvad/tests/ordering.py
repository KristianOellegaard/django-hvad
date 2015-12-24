from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal
from hvad.test_utils.fixtures import NormalFixture
from hvad.exceptions import WrongManager

class OrderingTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_minus_order_by(self):
        qs = Normal.objects.language('en').order_by('-shared_field')
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))

        qs = Normal.objects.language('en').order_by('-translated_field')
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))

    def test_order_by(self):
        qs = Normal.objects.language('en').order_by('shared_field')
        self.assertEqual(tuple(obj.pk for obj in qs), tuple(self.normal_id.values()))

        qs = Normal.objects.language('en').order_by('translated_field')
        self.assertEqual(tuple(obj.pk for obj in qs), tuple(self.normal_id.values()))

    def test_random_order(self):
        qs = Normal.objects.language('en').order_by('?')
        self.assertEqual(qs.count(), 2)
        self.assertCountEqual([obj.pk for obj in qs], tuple(self.normal_id.values()))

    def test_reverse(self):
        qs = Normal.objects.language('en').order_by('shared_field').reverse()
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))

        qs = Normal.objects.language('en').order_by('translated_field').reverse()
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))


class DefaultOrderingTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_checks(self):
        from django.db import models
        from hvad.models import TranslatableModel, TranslatedFields

        class ModelWithOrdering1(TranslatableModel):
            translations = TranslatedFields(
                translated_field=models.CharField(max_length=50),
            )
            class Meta:
                ordering = ('translated_field',)
        errors = ModelWithOrdering1.check()
        self.assertFalse(errors)

        class ModelWithOrdering2(TranslatableModel):
            translations = TranslatedFields(
                translated_field=models.CharField(max_length=50),
            )
            class Meta:
                ordering = ('language_code',)
        errors = ModelWithOrdering2.check()
        self.assertTrue(errors)

    def test_minus_order_by_shared(self):
        class ProxyWithOrder1(Normal):
            class Meta:
                proxy = True
                ordering = ('-shared_field',)

        qs = ProxyWithOrder1.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))

        qs = ProxyWithOrder1.objects.untranslated()
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))

    def test_order_by_shared(self):
        class ProxyWithOrder2(Normal):
            class Meta:
                proxy = True
                ordering = ('shared_field',)

        qs = ProxyWithOrder2.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs), tuple(self.normal_id.values()))

        qs = ProxyWithOrder2.objects.untranslated()
        self.assertEqual(tuple(obj.pk for obj in qs), tuple(self.normal_id.values()))

    def test_minus_order_by_translated(self):
        class ProxyWithOrder3(Normal):
            class Meta:
                proxy = True
                ordering = ('-translated_field',)

        qs = ProxyWithOrder3.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))

        qs = ProxyWithOrder3.objects.untranslated()
        self.assertRaises(WrongManager, len, qs)

    def test_order_by_translated(self):
        class ProxyWithOrder4(Normal):
            class Meta:
                proxy = True
                ordering = ('translated_field',)

        qs = ProxyWithOrder4.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs), tuple(self.normal_id.values()))

        qs = ProxyWithOrder4.objects.untranslated()
        self.assertRaises(WrongManager, len, qs)

    def test_ordered_fallback_no_raise(self):
        class ProxyWithOrder5(Normal):
            class Meta:
                proxy = True
                ordering = ('translated_field',)

        qs = ProxyWithOrder5.objects.untranslated()
        self.assertEqual(qs.count(), self.normal_count)
        pk = self.normal_id[1]
        self.assertEqual(qs.get(pk=pk).pk, pk)
        self.assertEqual(qs.in_bulk([pk])[pk].pk, pk)

        qs = qs.order_by('-shared_field')
        self.assertEqual(qs.first().pk, self.normal_id[self.normal_count])
        self.assertEqual(qs.last().pk, self.normal_id[1])
        self.assertEqual(tuple(obj.pk for obj in qs),
                         tuple(reversed(tuple(self.normal_id.values()))))
        self.assertEqual(len(qs), self.normal_count)
