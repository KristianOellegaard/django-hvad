# -*- coding: utf-8 -*-
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal


class FilterTests(NaniTestCase):
    fixtures = ['double_normal.json']
    
    data = {
        1: {
            'shared_field': 'Shared1',
            'translated_field_en': 'English1',
            'translated_field_ja': u'日本語一',
        },
        2: {
            'shared_field': 'Shared2',
            'translated_field_en': 'English2',
            'translated_field_ja': u'日本語二',
        },
    }
    
    def test_simple_filter(self):
        qs = Normal.objects.filter(shared_field__contains='2', language_code='en')
        self.assertEqual(qs.count(), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, self.data[2]['shared_field'])
        self.assertEqual(obj.translated_field, self.data[2]['translated_field_en'])
        qs = Normal.objects.filter(shared_field__contains='1', language_code='ja')
        self.assertEqual(qs.count(), 1)
        obj = qs[0]
        self.assertEqual(obj.shared_field, self.data[1]['shared_field'])
        self.assertEqual(obj.translated_field, self.data[1]['translated_field_ja'])
        
    def test_translated_filter(self):
        qs = Normal.objects.filter(translated_field__contains='English')
        self.assertEqual(qs.count(), 2)
        obj1, obj2 = qs
        self.assertEqual(obj1.shared_field, self.data[1]['shared_field'])
        self.assertEqual(obj1.translated_field, self.data[1]['translated_field_en'])
        self.assertEqual(obj2.shared_field, self.data[2]['shared_field'])
        self.assertEqual(obj2.translated_field, self.data[2]['translated_field_en'])


class IterTests(NaniTestCase):
    fixtures = ['double_normal.json']
    
    data = {
        1: {
            'shared_field': 'Shared1',
            'translated_field_en': 'English1',
            'translated_field_ja': u'日本語一',
        },
        2: {
            'shared_field': 'Shared2',
            'translated_field_en': 'English2',
            'translated_field_ja': u'日本語二',
        },
    }
    
    def test_simple_iter(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                index = 0
                for obj in Normal.objects.all():
                    index += 1
                    self.assertEqual(obj.shared_field, self.data[index]['shared_field'])
                    self.assertEqual(obj.translated_field, self.data[index]['translated_field_en'])
        with LanguageOverride('ja'):
            with self.assertNumQueries(1):
                index = 0
                for obj in Normal.objects.all():
                    index += 1
                    self.assertEqual(obj.shared_field, self.data[index]['shared_field'])
                    self.assertEqual(obj.translated_field, self.data[index]['translated_field_ja'])