# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal, Standard


class NormalAdminTests(NaniTestCase):
    fixtures = ['superuser.json']
    
    def test_admin_simple(self):
        SHARED = 'shared'
        TRANS = 'trans'
        self.client.login(username='admin', password='admin')
        url = reverse('admin:app_normal_add')
        data = {
            'shared_field': SHARED,
            'translated_field': TRANS,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Normal.objects.count(), 1)
        obj = Normal.objects.all()[0]
        self.assertEqual(obj.shared_field, SHARED)
        self.assertEqual(obj.translated_field, TRANS)
    
    def test_admin_dual(self):
        SHARED = 'shared'
        TRANS_EN = 'English'
        TRANS_JA = u'日本語'
        self.client.login(username='admin', password='admin')
        url = reverse('admin:app_normal_add')
        data_en = {
            'shared_field': SHARED,
            'translated_field': TRANS_EN,
        }
        data_ja = {
            'shared_field': SHARED,
            'translated_field': TRANS_JA,
        }
        with LanguageOverride('en'):
            response = self.client.post(url, data_en)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(Normal.objects.count(), 1)
        with LanguageOverride('ja'):
            response = self.client.post(url, data_ja)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(Normal.objects.count(), 2)
        en = Normal.objects.get(language_code='en')
        self.assertEqual(en.shared_field, SHARED)
        self.assertEqual(en.translated_field, TRANS_EN)
        ja = Normal.objects.get(language_code='ja')
        self.assertEqual(ja.shared_field, SHARED)
        self.assertEqual(ja.translated_field, TRANS_JA)
        
    def test_admin_standard(self):
        NORMAL = 'normal'
        self.client.login(username='admin', password='admin')
        url = reverse('admin:app_standard_add')
        data = {
            'normal_field': NORMAL,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Standard.objects.count(), 1)
        obj = Standard.objects.all()[0]
        self.assertEqual(obj.normal_field, NORMAL)