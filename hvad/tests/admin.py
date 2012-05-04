# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.test.client import Client
from hvad.admin import InlineModelForm
from hvad.admin import translatable_modelform_factory
from hvad.forms import TranslatableModelForm
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.fixtures import (TwoTranslatedNormalMixin, SuperuserMixin, 
    OneSingleTranslatedNormalMixin)
from hvad.test_utils.request_factory import RequestFactory
from hvad.test_utils.testcase import NaniTestCase
from hvad.test_utils.context_managers import SettingsOverride
from testproject.app.models import Normal, SimpleRelated, Other

class BaseAdminTests(object):
    def _get_admin(self, model):
        return admin.site._registry[model]


class NormalAdminTests(NaniTestCase, BaseAdminTests, SuperuserMixin):

    def test_lazy_translation_getter(self):
        translated_field_value = u"rød grød med fløde"
        slovenian_string = u'pozdravčki čćžđš'
        normal = Normal.objects.language("da").create(
            shared_field = "shared field",
            translated_field = translated_field_value,
        )
        normal_si = Normal.objects.get(pk=normal.pk).translate('sl')
        normal_si.translated_field = slovenian_string
        normal_si.save()


        Other.objects.create(normal=normal)
        self.assertEqual(normal.lazy_translation_getter("translated_field"), translated_field_value)
        n2 =  Normal.objects.get(pk=normal.pk)
        self.assertEqual(n2.safe_translation_getter("translated_field"), None)
        self.assertEqual(n2.lazy_translation_getter("translated_field"), translated_field_value)
        self.assertEqual(n2.safe_translation_getter("translated_field"), translated_field_value)

        with LanguageOverride('sl'):
            n2 =  Normal.objects.get(pk=normal.pk)
            self.assertEqual(n2.safe_translation_getter("translated_field"), None)
            self.assertEqual(n2.lazy_translation_getter("translated_field"), slovenian_string)
            self.assertEqual(n2.safe_translation_getter("translated_field"), slovenian_string)

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

    def test_get_available_languages(self):
        en = Normal.objects.language('en').create(shared_field='shared',
                                                  translated_field='english')
        admin = self._get_admin(Normal)
        self.assertEqual(list(admin.get_available_languages(en)), ['en'])
        self.assertEqual(list(admin.get_available_languages(None)), [])
            
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
        with LanguageOverride('en'):
            with self.login_user_context(username='admin', password='admin'):
                SHARED = 'shared'
                TRANS = 'trans'
                url = reverse('admin:app_normal_add')
                data = {
                    'shared_field': SHARED,
                    'translated_field': TRANS,
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(Normal.objects.count(), 1)
                obj = Normal.objects.language('en')[0]
                self.assertEqual(obj.shared_field, SHARED)
                self.assertEqual(obj.translated_field, TRANS)
    
    def test_admin_change_form_title(self):
        with LanguageOverride('en'):
            with self.login_user_context(username='admin', password='admin'):
                obj = Normal.objects.language('en').create(
                    shared_field="shared",
                    translated_field='English',
                )
                url = reverse('admin:app_normal_change', args=(obj.pk,))
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue('en' in response.content)
    
    def test_admin_change_form_redirect_add_another(self):
        lang = 'en'
        with LanguageOverride('ja'):
            with self.login_user_context(username='admin', password='admin'):
                obj = Normal.objects.language(lang).create(
                    shared_field="shared",
                    translated_field='English',
                )
                url = '%s?language=%s' % (reverse('admin:app_normal_change', args=(obj.pk,)), lang)
                data = {
                    'translated_field': 'English NEW',
                    'shared_field': obj.shared_field,
                    '_addanother': '1',
                    
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }

                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302, response.content)
                expected_url = '%s?language=%s' % (reverse('admin:app_normal_add'), lang)
                self.assertTrue(response['Location'].endswith(expected_url))
                obj = Normal.objects.language('en').get(pk=obj.pk)
                self.assertEqual(obj.translated_field, "English NEW")
    
    def test_admin_change_form_redirect_continue_edit(self):
        lang = 'en'
        with LanguageOverride('ja'):
            with self.login_user_context(username='admin', password='admin'):
                obj = Normal.objects.language(lang).create(
                    shared_field="shared",
                    translated_field='English',
                )
                url = '%s?language=%s' % (reverse('admin:app_normal_change', args=(obj.pk,)), lang)
                data = {
                    'translated_field': 'English NEW',
                    'shared_field': obj.shared_field,
                    '_continue': '1',
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302, response.content)
                self.assertTrue(response['Location'].endswith(url))
                obj = Normal.objects.language('en').get(pk=obj.pk)
                self.assertEqual(obj.translated_field, "English NEW")
                url2 = reverse('admin:app_normal_change', args=(obj.pk,))
                data = {
                    'translated_field': 'Japanese',
                    'shared_field': obj.shared_field,
                    '_continue': '1',
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post(url2, data)
                self.assertEqual(response.status_code, 302, response.content)
                self.assertTrue(response['Location'].endswith(url2))
                obj = Normal.objects.language('ja').get(pk=obj.pk)
                self.assertEqual(obj.translated_field, "Japanese")
                obj = Normal.objects.language('en').get(pk=obj.pk)
                self.assertEqual(obj.translated_field, "English NEW")
    
    def test_admin_change_form(self):
        lang = 'en'
        with LanguageOverride(lang):
            with self.login_user_context(username='admin', password='admin'):
                obj = Normal.objects.language(lang).create(
                    shared_field="shared",
                    translated_field='English',
                )
                url = reverse('admin:app_normal_change', args=(obj.pk,))
                data = {
                    'translated_field': 'English NEW',
                    'shared_field': obj.shared_field,
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post(url, data)
                expected_url = reverse('admin:app_normal_changelist')
                self.assertEqual(response.status_code, 302, response.content)
                self.assertTrue(response['Location'].endswith(expected_url))
                obj = Normal.objects.language('en').get(pk=obj.pk)
                self.assertEqual(obj.translated_field, "English NEW")
    
    def test_admin_dual(self):
        SHARED = 'shared'
        TRANS_EN = 'English'
        TRANS_JA = u'日本語'
        with self.login_user_context(username='admin', password='admin'):
            url = reverse('admin:app_normal_add')
            data_en = {
                'shared_field': SHARED,
                'translated_field': TRANS_EN,
                'simplerel-TOTAL_FORMS': '0',
                'simplerel-INITIAL_FORMS': '0',
                'simplerel-MAX_NUM_FORMS': '0',
            }
            data_ja = {
                'shared_field': SHARED,
                'translated_field': TRANS_JA,
                'simplerel-TOTAL_FORMS': '0',
                'simplerel-INITIAL_FORMS': '0',
                'simplerel-MAX_NUM_FORMS': '0',
            }
            with LanguageOverride('en'):
                response = self.client.post(url, data_en)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(Normal.objects.count(), 1)
            with LanguageOverride('ja'):
                response = self.client.post(url, data_ja)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(Normal.objects.count(), 2)
            en = Normal.objects.using_translations().get(language_code='en')
            self.assertEqual(en.shared_field, SHARED)
            self.assertEqual(en.translated_field, TRANS_EN)
            ja = Normal.objects.using_translations().get(language_code='ja')
            self.assertEqual(ja.shared_field, SHARED)
            self.assertEqual(ja.translated_field, TRANS_JA)
    
    def test_admin_with_param(self):
        with LanguageOverride('ja'):
            with self.login_user_context(username='admin', password='admin'):
                SHARED = 'shared'
                TRANS = 'trans'
                url = reverse('admin:app_normal_add')
                data = {
                    'shared_field': SHARED,
                    'translated_field': TRANS,
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post("%s?language=en" % url, data)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(Normal.objects.count(), 1)
                obj = Normal.objects.language('en')[0]
                self.assertEqual(obj.shared_field, SHARED)
                self.assertEqual(obj.translated_field, TRANS)
    

class AdminEditTests(NaniTestCase, BaseAdminTests, TwoTranslatedNormalMixin,
                     SuperuserMixin):
    def test_changelist(self):
        url = reverse('admin:app_normal_changelist')
        request = self.request_factory.get(url)
        normaladmin = self._get_admin(Normal)
        with LanguageOverride('en'):
            queryset = normaladmin.queryset(request)
            self.assertEqual(queryset.count(), 2)


class AdminDeleteTranslationsTests(NaniTestCase, BaseAdminTests, SuperuserMixin):
    def test_delete_last_translation(self):
        en = Normal.objects.language('en').create(shared_field='shared',
                                                  translated_field='english')
        url = reverse('admin:app_normal_delete_translation', args=(en.pk, 'en'))
        with self.login_user_context(username='admin', password='admin'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'admin/hvad/deletion_not_allowed.html')
        self.assertTrue(Normal.objects.language('en').get(pk=en.pk))
            
    def test_delete_translation_get(self):
        en = Normal.objects.language('en').create(shared_field='shared',
                                                  translated_field='english')
        ja = en.translate('ja')
        ja.translated_field = 'japanese'
        ja.save()
        url = reverse('admin:app_normal_delete_translation', args=(en.pk, 'en'))
        
        with self.login_user_context(username='admin', password='admin'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'admin/delete_confirmation.html')
        self.assertTrue(Normal.objects.language('en').get(pk=en.pk))
        self.assertTrue(Normal.objects.language('ja').get(pk=ja.pk))
    
    def test_delete_translation_post(self):
        en = Normal.objects.language('en').create(shared_field='shared',
                                                  translated_field='english')
        ja = en.translate('ja')
        ja.translated_field = 'japanese'
        ja.save()
        url = reverse('admin:app_normal_delete_translation', args=(en.pk, 'en'))
        
        with self.login_user_context(username='admin', password='admin'):
            response = self.client.post(url, {'post': 'yes'})
            self.assertEqual(response.status_code, HttpResponseRedirect.status_code)
        self.assertRaises(Normal.DoesNotExist, Normal.objects.language('en').get, pk=en.pk)
        self.assertTrue(Normal.objects.language('ja').get(pk=ja.pk))
    
    def test_delete_translation_no_obj(self):
        url = reverse('admin:app_normal_delete_translation', args=(1, 'en'))
        
        with self.login_user_context(username='admin', password='admin'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
    
    def test_delete_no_perms(self):
        user = User(username='staff', is_active=True, is_staff=True)
        user.set_password('staff')
        user.save()
        
        en = Normal.objects.language('en').create(shared_field='shared',
                                                  translated_field='english')
        ja = en.translate('ja')
        ja.translated_field = 'japanese'
        ja.save()
        url = reverse('admin:app_normal_delete_translation', args=(en.pk, 'en'))
        
        with self.login_user_context(username='staff', password='staff'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, HttpResponseForbidden.status_code)


class AdminNoFixturesTests(NaniTestCase, BaseAdminTests):
    def test_language_tabs(self):
        obj = Normal.objects.language("en").create(shared_field="shared",
                                                   translated_field="english")
        url = reverse('admin:app_normal_change', args=(1,))
        request = self.request_factory.get(url)
        normaladmin = self._get_admin(Normal)
        available_languages = []
        if obj:
            available_languages = obj.get_available_languages()
        tabs = normaladmin.get_language_tabs(request, available_languages)
        languages = settings.LANGUAGES
        self.assertEqual(len(languages), len(tabs))
        for tab, lang in zip(tabs, languages):
            _, tab_name, _, status = tab
            _, lang_name = lang
            self.assertEqual(tab_name, lang_name)
            if lang == "en":
                self.assertEqual(status, 'current')
            elif lang == "ja":
                self.assertEqual(status, 'available')
                
        with self.assertNumQueries(0) and LanguageOverride('en'):
            normaladmin.get_language_tabs(request, [])
    
    def test_get_change_form_base_template(self):
        normaladmin = self._get_admin(Normal)
        template = normaladmin.get_change_form_base_template()
        self.assertEqual(template, 'admin/change_form.html')
        
    def test_translatable_modelform_factory(self):
        t = translatable_modelform_factory('en', Normal, fields=['shared_field'], exclude=['id'])
        self.assertEqual(t.Meta.fields, ['shared_field'])
        self.assertEqual(t.Meta.exclude, ['id', 'language_code'])
        
        t = translatable_modelform_factory('en', Normal, fields=['shared_field'], exclude=['id'])
        self.assertEqual(t.Meta.fields, ['shared_field'])
        self.assertEqual(t.Meta.exclude, ['id', 'language_code'])
        
        class TestForm(TranslatableModelForm):
            class Meta:
                fields = ['shared_field'] 
                exclude = ['id']
               
        t = translatable_modelform_factory('en', Normal, form=TestForm)
        self.assertEqual(t.Meta.fields, ['shared_field'])
        self.assertEqual(t.Meta.exclude, ['id', 'language_code'])
        

class AdminRelationTests(NaniTestCase, BaseAdminTests, SuperuserMixin,
                         OneSingleTranslatedNormalMixin):
    def test_adding_related_object(self):
        url = reverse('admin:app_simplerelated_add')
        expected_url = reverse('admin:app_simplerelated_change', args=(1,))
        TRANS_FIELD = "English Content" 
        with LanguageOverride('en'):
            en = Normal.objects.all()[0]
            with self.login_user_context(username='admin', password='admin'):
                data = {
                    'normal': en.pk,
                    'translated_field': TRANS_FIELD,
                    '_continue': '1',
                }
                response = self.client.post(url, data)
                self.assertRedirects(response, expected_url)
            
            simplerel = SimpleRelated.objects.all()[0]
            self.assertEqual(simplerel.normal.pk, en.pk)
            self.assertEqual(simplerel.translated_field, TRANS_FIELD)



class TranslatableInlineAdminTests(NaniTestCase, BaseAdminTests, SuperuserMixin):
    def test_correct_id_in_inline(self):
        LANGUAGES = (
            ('en', u'English'),
            ('fr', u'Français'),
            ('da', u'Dansk'),
            ('ja', u'日本語'),
        )
        with SettingsOverride(LANGUAGES=LANGUAGES):
            with LanguageOverride('en'):
                normal = Normal.objects.language().create(shared_field="whatever1", translated_field="whatever in another language1")
                normal2 = Normal.objects.language().create(shared_field="whatever2", translated_field="whatever in another language2")
                normal3 = Normal.objects.language().create(shared_field="whatever3", translated_field="whatever in another language3")

            simple1 = SimpleRelated.objects.language("en").create(normal=normal3, translated_field="inline whatever translated")

            simple1.translate("ja")
            simple1.translated_field ="japanese stuff"
            simple1.save()

            simple1.translate("fr")
            simple1.translated_field ="french stuff"
            simple1.save()

            simple1.translate("da")
            simple1.translated_field ="danish stuff"
            simple1.save()


            with LanguageOverride('da'):
                instance = SimpleRelated.objects.get(pk=simple1.pk)
                class ExampleInlineForm(InlineModelForm):
                    class Meta:
                        model = SimpleRelated
                form = ExampleInlineForm(instance=instance)

                self.assertTrue(form.initial["id"] == instance.id)