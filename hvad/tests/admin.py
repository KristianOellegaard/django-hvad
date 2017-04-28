# -*- coding: utf-8 -*-
import django
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
if django.VERSION >= (1, 10):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse
from django.utils import translation
from django.http import HttpResponseForbidden, HttpResponseRedirect, QueryDict
from hvad.admin import InlineModelForm
from hvad.admin import translatable_modelform_factory
from hvad.compat import urlparse
from hvad.forms import TranslatableModelForm
from hvad.test_utils.fixtures import NormalFixture, UsersFixture
from hvad.test_utils.data import NORMAL
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, Unique, SimpleRelated, AutoPopulated


class BaseAdminTests(object):
    def _get_admin(self, model):
        return admin.site._registry[model]


class ModelHelpersTests(HvadTestCase, NormalFixture):
    normal_count = 1
    translations = ('en', 'ja')

    def test_translation_getters_cached(self):
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])

        # Translation getters should use the cached translation
        with self.assertNumQueries(0):
            self.assertEqual(obj.safe_translation_getter('translated_field'),
                             NORMAL[1].translated_field['en'])
            self.assertEqual(obj.lazy_translation_getter('translated_field'),
                             NORMAL[1].translated_field['en'])

        # Translation getters should use the cached translation
        # regardless of current language settings
        with translation.override('ja'):
            with self.assertNumQueries(0):
                self.assertEqual(obj.safe_translation_getter('translated_field'),
                                 NORMAL[1].translated_field['en'])
                self.assertEqual(obj.lazy_translation_getter('translated_field'),
                                 NORMAL[1].translated_field['en'])

    def test_translation_getters_uncached(self):
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])

        with translation.override('ja'):
            # Safe translation getter must not trigger a query
            with self.assertNumQueries(0):
                self.assertEqual(obj.safe_translation_getter('translated_field'),
                                 None)
            # Lazy translation getter must find something
            with self.assertNumQueries(1):
                self.assertEqual(obj.lazy_translation_getter('translated_field'),
                                 NORMAL[1].translated_field['ja'])
            # Lazy must have cached the translations
            with self.assertNumQueries(0):
                self.assertEqual(obj.safe_translation_getter('translated_field'),
                                 NORMAL[1].translated_field['ja'])

    def test_translation_getters_missing(self):
        # Try when both current language and first fallbacks are missing
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.settings(LANGUAGE_CODE='tt',
                           LANGUAGES=(('tt', 'Missing'),
                                      ('en', 'English'),
                                      ('ja', 'Japanese'))):
            with translation.override('th'):
                self.assertEqual(obj.lazy_translation_getter('translated_field'),
                                    NORMAL[1].translated_field['en'])

        # Now try with a different fallback priority
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.settings(LANGUAGE_CODE='tt',
                           LANGUAGES=(('tt', 'Missing'),
                                      ('ja', 'Japanese'),
                                      ('en', 'English'))):
            with translation.override('th'):
                self.assertEqual(obj.lazy_translation_getter('translated_field'),
                                    NORMAL[1].translated_field['ja'])

    def test_translation_getters_no_match(self):
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.settings(LANGUAGE_CODE='tt',
                           LANGUAGES=(('tt', 'Missing'),
                                      ('sr', 'English'),
                                      ('de', 'Japanese'))):
            with translation.override('th'):
                self.assertIn(obj.lazy_translation_getter('translated_field'),
                              NORMAL[1].translated_field.values())

    def test_translation_getters_no_translation(self):
        Normal.objects.language('all').filter(pk=self.normal_id[1]).delete_translations()
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with translation.override('en'):
            self.assertEqual(obj.lazy_translation_getter('translated_field'), None)


class AdminMethodsTests(HvadTestCase, BaseAdminTests, NormalFixture):
    normal_count = 1

    def test_all_translations(self):
        # Create an unstranslated model and get the translations
        myadmin = self._get_admin(Normal)

        obj = Normal.objects.untranslated().create(shared_field="shared")
        self.assertEqual(myadmin.all_translations(obj), "")

        # Create a english translated model and make sure the active language
        # is highlighted in admin with <strong></strong>
        obj = Normal.objects.language("en").get(pk=self.normal_id[1])
        with translation.override('en'):
            # make sure no the call will not generate a spurious query in assertNumQueries
            ContentType.objects.get_for_model(Normal)
            with self.assertNumQueries(1):
                self.assertTrue(myadmin.all_translations(obj).find("<strong>") != -1)
            with self.assertNumQueries(1):
                # Entries should be linked to the corresponding translation page
                self.assertTrue(myadmin.all_translations(obj).find("?language=en") != -1)

        with translation.override('th'):
            with self.assertNumQueries(1):
                self.assertTrue(myadmin.all_translations(obj).find("<strong>") == -1)

        # An unsaved object, shouldn't have any translations
        obj = Normal()
        self.assertEqual(myadmin.all_translations(obj), "")

    def test_all_translations_prefetch_related(self):
        myadmin = self._get_admin(Normal)

        qs = Normal.objects.untranslated().prefetch_related('translations')
        obj = qs.get(pk=self.normal_id[1])
        with translation.override('en'):
            # make sure no the call will not generate a spurious query in assertNumQueries
            ContentType.objects.get_for_model(Normal)
            with self.assertNumQueries(0):
                self.assertTrue(myadmin.all_translations(obj).find("<strong>") != -1)
                # Entries should be linked to the corresponding translation page
                self.assertTrue(myadmin.all_translations(obj).find("?language=en") != -1)

        with translation.override('th'):
            with self.assertNumQueries(0):
                self.assertTrue(myadmin.all_translations(obj).find("<strong>") == -1)

    def test_get_available_languages(self):
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        admin = self._get_admin(Normal)
        self.assertRaises(NotImplementedError, admin.get_available_languages, obj)

    def test_get_object(self):
        # Check if it returns a model, if there is at least one translation
        myadmin = self._get_admin(Normal)
        get_request = self.request_factory.get('/admin/app/normal/')

        obj = Normal.objects.language("en").get(pk=self.normal_id[1])
        with translation.override('en'):
            self.assertEqual(myadmin.get_object(get_request, obj.pk).pk,
                             self.normal_id[1])
            self.assertEqual(myadmin.get_object(get_request, obj.pk).shared_field,
                             NORMAL[1].shared_field)
            self.assertEqual(myadmin.get_object(get_request, obj.pk).language_code, 'en')
            self.assertEqual(myadmin.get_object(get_request, obj.pk).translated_field,
                             NORMAL[1].translated_field['en'])

        with translation.override('th'):
            self.assertEqual(myadmin.get_object(get_request, obj.pk).pk,
                             self.normal_id[1])
            self.assertEqual(myadmin.get_object(get_request, obj.pk).shared_field,
                             NORMAL[1].shared_field)
            self.assertEqual(myadmin.get_object(get_request, obj.pk).language_code, 'th')
            self.assertEqual(myadmin.get_object(get_request, obj.pk).translated_field, '')

        # Check what happens if there is no translations at all
        obj = Normal.objects.untranslated().create(shared_field="shared")
        with translation.override('en'):
            self.assertIs(myadmin.get_object(get_request, obj.pk), None)

    def test_get_object_nonexisting(self):
        # In case the object doesnt exist, it should return None
        myadmin = self._get_admin(Normal)
        get_request = self.request_factory.get('/admin/app/normal/')
        self.assertEqual(myadmin.get_object(get_request, -1), None)

class NormalAdminTests(HvadTestCase, BaseAdminTests, UsersFixture, NormalFixture):
    normal_count = 1

    def test_admin_simple(self):
        with translation.override('en'):
            with self.login_user_context('admin'):
                SHARED = 'shared_new'
                TRANS = 'trans_new'
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
                self.assertEqual(Normal.objects.count(), self.normal_count + 1)
                obj = Normal.objects.language('en').get(shared_field=SHARED)
                self.assertEqual(obj.shared_field, SHARED)
                self.assertEqual(obj.translated_field, TRANS)

    def test_admin_duplicate_simple(self):
        with translation.override('en'):
            Unique.objects.language('en').create(
                shared_field='shared',
                translated_field='translated_duplicate',
                unique_by_lang='unique_by_lang_1',
            )
            with self.login_user_context('admin'):
                response = self.client.post(reverse('admin:app_unique_add'), {
                    'shared_field': 'shared2',
                    'translated_field': 'translated_duplicate',
                    'unique_by_lang': 'unique_by_lang_2',
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context_data['errors']), 1)
                self.assertEqual(Unique.objects.count(), 1)

    def test_admin_duplicate_by_lang(self):
        with translation.override('en'):
            Unique.objects.language('en').create(
                shared_field='shared',
                translated_field='translated',
                unique_by_lang='unique_by_lang_duplicate',
            )
            with self.login_user_context('admin'):
                response = self.client.post(reverse('admin:app_unique_add'), {
                    'shared_field': 'shared2',
                    'translated_field': 'translated2',
                    'unique_by_lang': 'unique_by_lang_duplicate',
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context_data['errors']), 1)
                self.assertEqual(Unique.objects.count(), 1)

    def test_admin_auto_populated(self):
        """
        This only works if we create the translation attribute before saving
        the instance. Otherwise the overridden save() method can't access the
        translated field during the initial save(), and it crashes.
        """

        with translation.override('en'):
            with self.login_user_context('admin'):
                danish_string = u"rød grød med fløde"
                url = reverse('admin:app_autopopulated_add')
                data = {
                    'translated_name': danish_string,
                }
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(AutoPopulated.objects.count(), 1)
                obj = AutoPopulated.objects.language('en').get()
                self.assertEqual(obj.translated_name, danish_string)
                self.assertEqual(obj.slug, "rd-grd-med-flde")

    def test_admin_change_form_title(self):
        with translation.override('en'):
            with self.login_user_context('admin'):
                url = reverse('admin:app_normal_change', args=(self.normal_id[1],))
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue('en' in response.content.decode('utf-8'))

    def test_admin_change_form_language_tabs(self):
        with self.settings(LANGUAGES=(('en', 'English'),
                                      ('fr', 'French'),
                                      ('ja', 'Japanese'))):
            with translation.override('en'):
                with self.login_user_context('admin'):
                    url = reverse('admin:app_normal_change', args=(self.normal_id[1],))
                    test_data = (
                        {},
                        {'_changelist_filters': 'q=searchparam'},
                        {'_changelist_filters': 'q=searchparam', 'language': 'fr'},
                    )

                    for data in test_data:
                        response = self.client.get(url, data=data)
                        self.assertEqual(response.status_code, 200)
                        tabs = response.context['language_tabs']

                        for actual_tab_url, name, key, status, del_url in tabs:
                            self.assertEqual(
                                QueryDict(urlparse(actual_tab_url).query).dict(),
                                dict(data, language=key)
                            )
                            self.assertEqual(url, urlparse(actual_tab_url).path)
                            self.assertEqual(status, 'current' if key == data.get('language', 'en') else
                                                     'available' if key in self.translations else
                                                     'empty')
                            expected_del_url = reverse('admin:app_normal_delete_translation',
                                                       args=(self.normal_id[1], key))
                            self.assertEqual(del_url, expected_del_url if key in self.translations else None)

    def test_admin_change_form_action_url(self):
        with translation.override('en'):
            with self.login_user_context('admin'):
                url = reverse('admin:app_normal_change', args=(self.normal_id[1],))
                tests = (
                    '',
                    'language=fr',
                    '_changelist_filters=q%3Dparam&language=fr',
                )
                for query_string in tests:
                    expected_dict = QueryDict(query_string)
                    full_url = '%s?%s' % (url, query_string) if query_string else url
                    response = self.client.get(full_url)
                    form_url = urlparse(response.context['form_url'])
                    self.assertEqual(expected_dict, QueryDict(form_url.query),
                                     'query_string=%r' % query_string)


    def test_admin_change_form_redirect_add_another(self):
        lang = 'en'
        with translation.override('ja'):
            with self.login_user_context('admin'):
                url = '%s?language=%s' % (reverse('admin:app_normal_change',
                                                  args=(self.normal_id[1],)), lang)
                data = {
                    'translated_field': 'English NEW',
                    'shared_field': NORMAL[1].shared_field,
                    '_addanother': '1',
                    
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }

                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302, response.content)
                expected_url = '%s?language=%s' % (reverse('admin:app_normal_add'), lang)
                self.assertTrue(response['Location'].endswith(expected_url))
                obj = Normal.objects.language('en').get(pk=self.normal_id[1])
                self.assertEqual(obj.translated_field, "English NEW")
    
    def test_admin_change_form_redirect_continue_edit(self):
        lang = 'en'
        with translation.override('ja'):
            with self.login_user_context('admin'):
                url = '%s?language=%s' % (reverse('admin:app_normal_change',
                                                  args=(self.normal_id[1],)), lang)
                data = {
                    'translated_field': 'English NEW',
                    'shared_field': NORMAL[1].shared_field,
                    '_continue': '1',
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302, response.content)
                self.assertTrue(response['Location'].endswith(url))
                obj = Normal.objects.language('en').get(pk=self.normal_id[1])
                self.assertEqual(obj.translated_field, "English NEW")
                url2 = reverse('admin:app_normal_change', args=(self.normal_id[1],))
                data = {
                    'translated_field': 'Japanese',
                    'shared_field': NORMAL[1].shared_field,
                    '_continue': '1',
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post(url2, data)
                self.assertEqual(response.status_code, 302, response.content)
                self.assertTrue(response['Location'].endswith(url2))
                obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
                self.assertEqual(obj.translated_field, "Japanese")
                obj = Normal.objects.language('en').get(pk=self.normal_id[1])
                self.assertEqual(obj.translated_field, "English NEW")

    def test_admin_change_form(self):
        with translation.override('en'):
            with self.login_user_context('admin'):
                url = reverse('admin:app_normal_change', args=(self.normal_id[1],))
                data = {
                    'translated_field': 'English NEW',
                    'shared_field': NORMAL[1].shared_field,
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                }
                response = self.client.post(url, data)
                expected_url = reverse('admin:app_normal_changelist')
                self.assertEqual(response.status_code, 302, response.content)
                self.assertTrue(response['Location'].endswith(expected_url))
                obj = Normal.objects.language('en').get(pk=self.normal_id[1])
                self.assertEqual(obj.translated_field, "English NEW")

    def test_admin_dual(self):
        SHARED = 'shared_new'
        TRANS_EN = 'English'
        TRANS_JA = u'日本語'
        with self.login_user_context('admin'):
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
            with translation.override('en'):
                response = self.client.post(url, data_en)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(Normal.objects.untranslated().count(), self.normal_count + 1)
            with translation.override('ja'):
                response = self.client.post(url, data_ja)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(Normal.objects.untranslated().count(), self.normal_count + 2)
            en = Normal.objects.language('en').get(shared_field=SHARED)
            self.assertEqual(en.shared_field, SHARED)
            self.assertEqual(en.translated_field, TRANS_EN)
            ja = Normal.objects.language('ja').get(shared_field=SHARED)
            self.assertEqual(ja.shared_field, SHARED)
            self.assertEqual(ja.translated_field, TRANS_JA)

    def test_admin_with_param(self):
        with translation.override('ja'):
            with self.login_user_context('admin'):
                SHARED = 'shared_new'
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
                self.assertEqual(Normal.objects.untranslated().count(), self.normal_count + 1)
                obj = Normal.objects.language('en').get(shared_field=SHARED)
                self.assertEqual(obj.shared_field, SHARED)
                self.assertEqual(obj.translated_field, TRANS)

    def test_admin_change_popup(self):
        from django.contrib.admin.options import IS_POPUP_VAR
        with translation.override('en'):
            with self.login_user_context('admin'):
                url = reverse('admin:app_normal_change', args=(self.normal_id[1],))
                data = {
                    'translated_field': 'English NEW',
                    'shared_field': NORMAL[1].shared_field,
                    'simplerel-TOTAL_FORMS': '0',
                    'simplerel-INITIAL_FORMS': '0',
                    'simplerel-MAX_NUM_FORMS': '0',
                    IS_POPUP_VAR: '1',
                }
                response = self.client.post(url, data)
                self.assertIn(response.status_code, [200, 302], response.content)
                obj = Normal.objects.language('en').get(pk=self.normal_id[1])
                self.assertEqual(obj.translated_field, "English NEW")


class AdminEditTests(HvadTestCase, BaseAdminTests, NormalFixture, UsersFixture):
    normal_count = 2

    def test_changelist(self):
        url = reverse('admin:app_normal_changelist')
        request = self.request_factory.get(url)
        normaladmin = self._get_admin(Normal)
        with translation.override('en'):
            queryset = normaladmin.get_queryset(request)
            self.assertEqual(queryset.count(), self.normal_count)


class AdminDeleteTranslationsTests(HvadTestCase, BaseAdminTests, UsersFixture, NormalFixture):
    normal_count = 1
    translations = ('en', 'ja')

    def test_delete_last_translation(self):
        Normal.objects.language('ja').delete_translations()
        url = reverse('admin:app_normal_delete_translation', args=(self.normal_id[1], 'en'))
        with self.login_user_context('admin'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'admin/hvad/deletion_not_allowed.html')
        self.assertTrue(Normal.objects.language('en').filter(pk=self.normal_id[1]).exists())

    def test_delete_translation_get(self):
        url = reverse('admin:app_normal_delete_translation', args=(self.normal_id[1], 'en'))
        with self.login_user_context('admin'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'admin/delete_confirmation.html')
        self.assertTrue(Normal.objects.language('en').filter(pk=self.normal_id[1]).exists())
        self.assertTrue(Normal.objects.language('ja').filter(pk=self.normal_id[1]).exists())

    def test_delete_translation_post(self):
        url = reverse('admin:app_normal_delete_translation', args=(self.normal_id[1], 'en'))
        with self.login_user_context('admin'):
            response = self.client.post(url, {'post': 'yes'})
            self.assertEqual(response.status_code, HttpResponseRedirect.status_code)
            self.assertRaises(Normal.DoesNotExist,
                              Normal.objects.language('en').get, pk=self.normal_id[1])
        self.assertTrue(Normal.objects.language('ja').filter(pk=self.normal_id[1]).exists())

    def test_delete_translation_no_obj(self):
        url = reverse('admin:app_normal_delete_translation', args=(-1, 'en'))
        with self.login_user_context('admin'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

    def test_delete_no_perms(self):
        url = reverse('admin:app_normal_delete_translation', args=(self.normal_id[1], 'en'))
        with self.login_user_context('staff'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, HttpResponseForbidden.status_code)


class AdminNoFixturesTests(HvadTestCase, BaseAdminTests):
    def test_get_change_form_base_template(self):
        normaladmin = self._get_admin(Normal)
        template = normaladmin.get_change_form_base_template()

        #HACK navigate through incompatibility between django template engine
        # deprecation path and django extends tag in version 1.8
        if hasattr(template, 'template'):
            template = template.template
        self.assertEqual(template.name, 'admin/change_form.html')
        
    def test_translatable_modelform_factory(self):
        t = translatable_modelform_factory('en', Normal, fields=['shared_field'], exclude=['id'])
        self.assertCountEqual(t.Meta.fields, ['shared_field'])
        self.assertCountEqual(t.Meta.exclude, ['id', 'translations'])
        
        t = translatable_modelform_factory('en', Normal, fields=['shared_field'], exclude=['id'])
        self.assertCountEqual(t.Meta.fields, ['shared_field'])
        self.assertCountEqual(t.Meta.exclude, ['id', 'translations'])
        
        class TestForm(TranslatableModelForm):
            class Meta:
                fields = ['shared_field'] 
                exclude = ['id']
               
        t = translatable_modelform_factory('en', Normal, form=TestForm)
        self.assertCountEqual(t.Meta.fields, ['shared_field'])
        self.assertCountEqual(t.Meta.exclude, ['id', 'translations'])
        

class AdminRelationTests(HvadTestCase, BaseAdminTests, UsersFixture, NormalFixture):
    normal_count = 1

    def create_fixtures(self):
        super(AdminRelationTests, self).create_fixtures()
        self.simple = SimpleRelated.objects.language('en').create(
            normal_id=self.normal_id[1], translated_field='English inline'
        )
        self.simple.translated_fields.create(language_code='fr', translated_field='French inline')
        self.simple.translated_fields.create(language_code='da', translated_field='Danish inline')

    def test_correct_id_in_inline(self):
        with translation.override('da'):
            instance = SimpleRelated.objects.get(pk=self.simple.pk)
            class ExampleInlineForm(InlineModelForm):
                class Meta:
                    model = SimpleRelated
                    exclude = []
            form = ExampleInlineForm(instance=instance)

            self.assertTrue(form.initial["id"] == instance.id)

    def test_adding_related_object(self):
        url = reverse('admin:app_simplerelated_add')
        TRANS_FIELD = "English Content" 
        with translation.override('en'):
            en = Normal.objects.get(pk=self.normal_id[1])
            with self.login_user_context('admin'):
                data = {
                    'normal': self.normal_id[1],
                    'translated_field': TRANS_FIELD,
                    '_continue': '1',
                }
                response = self.client.post(url, data)

                simplerel = SimpleRelated.objects.language().get(translated_field=TRANS_FIELD)
                self.assertEqual(simplerel.normal.pk, en.pk)

                expected_url = reverse('admin:app_simplerelated_change', args=(simplerel.pk,))
                self.assertRedirects(response, expected_url)
