# -*- coding: utf-8 -*-
import django
from hvad.test_utils.data import DOUBLE_NORMAL
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal
from hvad.test_utils.fixtures import TwoTranslatedNormalMixin
from hvad.exceptions import WrongManager

class OrderingTest(HvadTestCase, TwoTranslatedNormalMixin):
    def setUp(self):
        super(OrderingTest, self).setUp()
        self.a = Normal.objects.language('en').get(shared_field=DOUBLE_NORMAL[1]['shared_field'])
        self.b = Normal.objects.language('en').get(shared_field=DOUBLE_NORMAL[2]['shared_field'])

    def test_minus_order_by(self):
        qs = Normal.objects.language('en').order_by('-shared_field')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))

        qs = Normal.objects.language('en').order_by('-translated_field')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))

    def test_order_by(self):
        qs = Normal.objects.language('en').order_by('shared_field')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.a.pk, self.b.pk))

        qs = Normal.objects.language('en').order_by('translated_field')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.a.pk, self.b.pk))

    def test_random_order(self):
        qs = Normal.objects.language('en').order_by('?')
        self.assertEqual(qs.count(), 2)
        pks = [obj.pk for obj in qs]
        self.assertTrue(self.a.pk in pks)
        self.assertTrue(self.b.pk in pks)

    def test_reverse(self):
        qs = Normal.objects.language('en').order_by('shared_field').reverse()
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))

        qs = Normal.objects.language('en').order_by('translated_field').reverse()
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))


class DefaultOrderingTest(HvadTestCase, TwoTranslatedNormalMixin):
    def setUp(self):
        super(DefaultOrderingTest, self).setUp()
        self.a = Normal.objects.language('en').get(shared_field=DOUBLE_NORMAL[1]['shared_field'])
        self.b = Normal.objects.language('en').get(shared_field=DOUBLE_NORMAL[2]['shared_field'])

    def test_minus_order_by_shared(self):
        class ProxyWithOrder1(Normal):
            class Meta:
                proxy = True
                ordering = ('-shared_field',)

        qs = ProxyWithOrder1.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))

        qs = ProxyWithOrder1.objects.untranslated()
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))

    def test_order_by_shared(self):
        class ProxyWithOrder2(Normal):
            class Meta:
                proxy = True
                ordering = ('shared_field',)

        qs = ProxyWithOrder2.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.a.pk, self.b.pk))

        qs = ProxyWithOrder2.objects.untranslated()
        self.assertEqual(tuple(obj.pk for obj in qs), (self.a.pk, self.b.pk))

    def test_minus_order_by_translated(self):
        class ProxyWithOrder3(Normal):
            class Meta:
                proxy = True
                ordering = ('-translated_field',)

        qs = ProxyWithOrder3.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))

        qs = ProxyWithOrder3.objects.untranslated()
        self.assertRaises(WrongManager, len, qs)

    def test_order_by_translated(self):
        class ProxyWithOrder4(Normal):
            class Meta:
                proxy = True
                ordering = ('translated_field',)

        qs = ProxyWithOrder4.objects.language('en')
        self.assertEqual(tuple(obj.pk for obj in qs), (self.a.pk, self.b.pk))

        qs = ProxyWithOrder4.objects.untranslated()
        self.assertRaises(WrongManager, len, qs)

    def test_ordered_fallback_no_raise(self):
        class ProxyWithOrder5(Normal):
            class Meta:
                proxy = True
                ordering = ('translated_field',)

        qs = ProxyWithOrder5.objects.untranslated()
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs.get(pk=1).pk, 1)
        self.assertEqual(qs.in_bulk([1])[1].pk, 1)

        qs = qs.order_by('-shared_field')
        if django.VERSION >= (1, 6):
            self.assertEqual(qs.first().pk, self.b.pk)
            self.assertEqual(qs.last().pk, self.a.pk)
        self.assertEqual(tuple(obj.pk for obj in qs), (self.b.pk, self.a.pk))
        self.assertEqual(len(qs), 2)

