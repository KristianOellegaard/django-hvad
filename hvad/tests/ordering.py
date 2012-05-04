# -*- coding: utf-8 -*-
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal

class OrderingTest(NaniTestCase):
    def test_minus_order_by(self):
        a = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="A")
        b = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="B")
        qs = Normal.objects.language('en').order_by('-shared_field')
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].pk, b.pk)
        self.assertEqual(qs[1].pk, a.pk)
        
    def test_order_by(self):
        a = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="A")
        b = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="B")
        qs = Normal.objects.language('en').order_by('shared_field')
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].pk, a.pk)
        self.assertEqual(qs[1].pk, b.pk)
    
    def test_random_order(self):
        a = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="A")
        b = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="B")
        qs = Normal.objects.language('en').order_by('?')
        self.assertEqual(qs.count(), 2)
        pks = [obj.pk for obj in qs]
        self.assertTrue(a.pk in pks)
        self.assertTrue(b.pk in pks)
        
    def test_reverse(self):
        a = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="A")
        b = Normal.objects.language('en').create(translated_field = "English",
                                                 shared_field="B")
        qs = Normal.objects.language('en').order_by('shared_field').reverse()
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].pk, b.pk)
        self.assertEqual(qs[1].pk, a.pk)