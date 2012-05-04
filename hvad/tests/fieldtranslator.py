# -*- coding: utf-8 -*-
from hvad.fieldtranslator import translate
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Related


class FieldtranslatorTests(NaniTestCase):
    def test_simple(self):
        INPUT = 'normal__shared_field'
        query_string, joins = translate(INPUT, Related)
        self.assertEqual(query_string, INPUT)
        self.assertEqual(joins, ['normal__translations__language_code'])
        
    def test_query_bit(self):
        INPUT = 'normal__shared_field__exact'
        query_string, joins = translate(INPUT, Related)
        self.assertEqual(query_string, INPUT)
        self.assertEqual(joins, ['normal__translations__language_code'])
        INPUT = 'normal__translated_field__exact'
        query_string, joins = translate(INPUT, Related)
        self.assertEqual(query_string, 'normal__translations__translated_field__exact')
        self.assertEqual(joins, ['normal__translations__language_code'])