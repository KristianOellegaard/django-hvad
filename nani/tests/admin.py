# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase
from nani.test_utils.request_factory import RequestFactory
from testproject.app.models import Normal
from nani.admin import translatable_modelform_factory
from nani.forms import TranslatableModelForm 

class BaseAdminTests(object):
    def _get_admin(self, model):
        return admin.site._registry[model]

class NormalAdminTests(NaniTestCase, BaseAdminTests):
    fixtures = ['superuser.json']
    
    def test_all_translations(self):
        # Create an unstranslated model and get the translations
        myadmin = self._get_admin(Normal)
        obj = Normal.objects.untranslated().create(
            shared_field="shared",
        )
        self.assertEqual(myadmin.all_translations(obj), "")
        
        # Create a english translated model and make sure the active language
        # is highlighted in admin with <strong></strong>
        obj = Normal.objects.language("en").create(
            shared_field="shared",
        )
        with LanguageOverride('en'):
            self.assertEqual(myadmin.all_translations(obj), "<strong>en</strong>")
        
        with LanguageOverride('ja'):
            self.assertEqual(myadmin.all_translations(obj), "en")
            
        # An unsaved object, shouldnt have any translations
        
        obj = Normal()
        self.assertEqual(myadmin.all_translations(obj), "")
            
    def test_get_object(self):
        # Check if it returns a model, if there is at least one translation
        myadmin = self._get_admin(Normal)
        rf = RequestFactory()
        get_request = rf.get('/admin/app/normal/')
        
        obj = Normal.objects.language("en").create(
            shared_field="shared",
        )
        with LanguageOverride('en'):
            self.assertEqual(myadmin.get_object(get_request, obj.pk).pk, obj.pk)
            self.assertEqual(myadmin.get_object(get_request, obj.pk).shared_field, obj.shared_field)
            
        with LanguageOverride('ja'):
            self.assertEqual(myadmin.get_object(get_request, obj.pk).pk, obj.pk)
            self.assertEqual(myadmin.get_object(get_request, obj.pk).shared_field, obj.shared_field)
            
        # Check what happens if there is no translations at all
        obj = Normal.objects.untranslated().create(
            shared_field="shared",
        )
        self.assertEqual(myadmin.get_object(get_request, obj.pk).pk, obj.pk)
        self.assertEqual(myadmin.get_object(get_request, obj.pk).shared_field, obj.shared_field)
        
            
    def test_get_object_nonexisting(self):
        # In case the object doesnt exist, it should return None
        myadmin = self._get_admin(Normal)
        rf = RequestFactory()
        get_request = rf.get('/admin/app/normal/')
        
        self.assertEqual(myadmin.get_object(get_request, 1231), None)
            
    def test_admin_simple(self):
        SHARED = 'shared'
        TRANS = 'trans'
        self.client.login(username='admin', password='admin')
        url = reverse('admin:app_normal_add')
        data = {
            'shared_field': SHARED,
            'translated_field': TRANS,
            'language_code': 'en',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Normal.objects.count(), 1)
        obj = Normal.objects.language('en')[0]
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
            'language_code': 'en',
        }
        data_ja = {
            'shared_field': SHARED,
            'translated_field': TRANS_JA,
            'language_code': 'ja',
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


class AdminEditTests(NaniTestCase, BaseAdminTests):
    fixtures = ['double_normal.json', 'superuser.json']
        
    def test_changelist(self):
        url = reverse('admin:app_normal_changelist')
        request = self.request_factory.get(url)
        normaladmin = self._get_admin(Normal)
        with LanguageOverride('en'):
            queryset = normaladmin.queryset(request)
            self.assertEqual(queryset.count(), 2)

class AdminNoFixturesTests(NaniTestCase, BaseAdminTests):
    def test_language_tabs(self):
        obj = Normal.objects.language("en").create(shared_field="shared", translated_field="english")
        url = reverse('admin:app_normal_change', args=(1,))
        request = self.request_factory.get(url)
        normaladmin = self._get_admin(Normal)
        tabs = normaladmin.get_language_tabs(request, obj)
        languages = settings.LANGUAGES
        self.assertEqual(len(languages), len(tabs))
        for tab, lang in zip(tabs, languages):
            _, tab_name, status = tab
            _, lang_name = lang
            self.assertEqual(tab_name, lang_name)
            if lang == "en":
                self.assertEqual(status, 'current')
            elif lang == "ja":
                self.assertEqual(status, 'available')
                
        with self.assertNumQueries(0) and LanguageOverride('en'):
            normaladmin.get_language_tabs(request, None)
    
    def test_get_change_form_base_template(self):
        normaladmin = self._get_admin(Normal)
        template = normaladmin.get_change_form_base_template()
        self.assertEqual(template, 'admin/change_form.html')
        
    def test_translatable_modelform_factory(self):
        t = translatable_modelform_factory(Normal, fields=['shared_field'], exclude=['id'])
        self.assertEqual(t.Meta.fields, ['shared_field'])
        self.assertEqual(t.Meta.exclude, ['id'])
        
        t = translatable_modelform_factory(Normal, fields=['shared_field'], exclude=['id'])
        self.assertEqual(t.Meta.fields, ['shared_field'])
        self.assertEqual(t.Meta.exclude, ['id'])
        
        class TestForm(TranslatableModelForm):
            class Meta:
               fields = ['shared_field'] 
               exclude = ['id']
               
        t = translatable_modelform_factory(Normal, form=TestForm)
        self.assertEqual(t.Meta.fields, ['shared_field'])
        self.assertEqual(t.Meta.exclude, ['id'])
        
