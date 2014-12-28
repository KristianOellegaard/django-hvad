# -*- coding: utf-8 -*-
from django import forms
from django.http import Http404
from django.contrib.auth.models import User
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.data import NORMAL
from hvad.test_utils.fixtures import NormalFixture
from hvad.test_utils.project.app.models import Normal
from hvad.forms import TranslatableModelForm
from hvad.views import (TranslatableCreateView, TranslatableUpdateView,
                        TranslatableDeleteView)

#=============================================================================

class TestCreateView(TranslatableCreateView):
    model = Normal
    success_url = '%(id)s'

class TestUpdateView(TranslatableUpdateView):
    model = Normal
    slug_field = 'shared_field'
    success_url = '%(id)s'

class TestDeleteView(TranslatableDeleteView):
    model = Normal
    slug_field = 'shared_field'

class DeprecatedObjectUpdateView(TranslatableUpdateView):
    model = Normal
    def _get_object(self, queryset=None):
        return Normal.objects.untranslated().get(pk=self.kwargs['pk'])

class DeprecatedLanguageUpdateView(TranslatableUpdateView):
    model = Normal
    def _language(self, request):
        return request.GET.get('lang')

class DeprecatedFilterUpdateView(TranslatableUpdateView):
    model = Normal
    def filter_kwargs(self):
        return {'shared_field': self.kwargs['custom']}

class DeprecatedContextUpdateView(TranslatableUpdateView):
    model = Normal
    def context_modifier_foo(self, **kwargs):
        return { 'modifier': 'foo' }

#=============================================================================

class CreateViewTests(HvadTestCase):
    def setUp(self):
        self.user = User.objects.create(username='admin', is_superuser=True)

    def test_get(self):
        'Display an empty form'
        with LanguageOverride('en'):
            request = self.request_factory.get('/url/')
            request.user = self.user

            response = TestCreateView.as_view()(request)
            self.assertEqual(response.status_code, 200)

    def test_post(self):
        'Create a new object in current language'
        with LanguageOverride('en'):
            # Valid form
            request = self.request_factory.post('/url/', {
                'shared_field': 'shared',
                'translated_field': 'translated',
            })
            request.user = self.user

            response = TestCreateView.as_view()(request)
            self.assertEqual(response.status_code, 302)
            obj = Normal.objects.language('en').get(pk=int(response['Location']))
            self.assertEqual(obj.shared_field, 'shared')
            self.assertEqual(obj.translated_field, 'translated')

            # Invalid form
            request = self.request_factory.post('/url/', {
                'shared_field': 'shared',
                'translated_field': 'x'*999,
            })
            request.user = self.user

            response = TestCreateView.as_view()(request)
            self.assertEqual(response.status_code, 200)

    def test_post_language(self):
        'Create a new object with given language'
        with LanguageOverride('en'):
            request = self.request_factory.post('/url/?language=ja', {
                'shared_field': 'shared',
                'translated_field': 'translated',
            })
            request.user = self.user

            response = TestCreateView.as_view()(request)
            self.assertEqual(response.status_code, 302)
            obj = Normal.objects.language('ja').get(pk=int(response['Location']))
            self.assertEqual(obj.shared_field, 'shared')
            self.assertEqual(obj.translated_field, 'translated')

            # Invalid form
            request = self.request_factory.post('/url/?language=ja', {
                'shared_field': 'shared_xx',
                'translated_field': 'x'*999,
            })
            request.user = self.user

            response = TestCreateView.as_view()(request)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Normal.objects.language('all').filter(shared_field='shared_xx').exists())

    def test_alternate_declarations(self):
        'A view with no model specified, should use that of the queryset'
        class QuerysetView(TranslatableCreateView):
            queryset = Normal.objects.untranslated()
            success_url = '%(id)s'
        request = self.request_factory.post('/url/?language=ja', {
            'shared_field': 'shared',
            'translated_field': 'translated',
        })
        request.user = self.user
        response = QuerysetView.as_view()(request)
        self.assertEqual(response.status_code, 302)

        class TranslationQuerysetView(TranslatableCreateView):
            queryset = Normal.objects.language()
            success_url = '%(id)s'
        request = self.request_factory.post('/url/?language=ja', {
            'shared_field': 'shared',
            'translated_field': 'translated',
        })
        request.user = self.user
        response = TranslationQuerysetView.as_view()(request)
        self.assertEqual(response.status_code, 302)

        class CustomFormView(TranslatableCreateView):
            model = Normal
            success_url = '%(id)s'
            class form_class(TranslatableModelForm):
                additional = forms.CharField(max_length=250)
        request = self.request_factory.post('/url/?language=ja', {
            'shared_field': 'shared',
            'translated_field': 'translated',
            'additional': 'more',
        })
        request.user = self.user
        response = CustomFormView.as_view()(request)
        self.assertEqual(response.status_code, 302)

class UpdateViewTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def setUp(self):
        super(UpdateViewTests, self).setUp()
        self.user = User.objects.create(username='admin', is_superuser=True)

    def test_get_default(self):
        'Display an existing object in a new form'
        with LanguageOverride('en'):
            # Using pk
            request = self.request_factory.get('/url/')
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[1])
            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertEqual(data['translated_field'], NORMAL[1].translated_field['en'])

            # Using slug
            request = self.request_factory.get('/url/')
            request.user = self.user
            response = TestUpdateView.as_view()(request, slug=NORMAL[1].shared_field)
            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertEqual(data['translated_field'], NORMAL[1].translated_field['en'])

            # Nonexistent object
            request = self.request_factory.get('/url/')
            request.user = self.user
            with self.assertRaises(Http404):
                response = TestUpdateView.as_view()(request, slug='nonexistent')

    def test_get_language(self):
        'Display an existing object in a new form with a specific language'
        with LanguageOverride('en'):
            # Using pk
            request = self.request_factory.get('/url/?language=ja')
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[1])
            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertEqual(data['translated_field'], NORMAL[1].translated_field['ja'])

            # Using slug
            request = self.request_factory.get('/url/?language=ja')
            request.user = self.user
            response = TestUpdateView.as_view()(request, slug=NORMAL[1].shared_field)
            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertEqual(data['translated_field'], NORMAL[1].translated_field['ja'])

            # Nonexistent translation, should display empty one
            request = self.request_factory.get('/url/?language=sr')
            request.user = self.user
            response = TestUpdateView.as_view()(request, slug=NORMAL[1].shared_field)
            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertIs(data.get('translated_field'), None)

            # Nonexistent object
            request = self.request_factory.get('/url/?language=ja')
            request.user = self.user
            with self.assertRaises(Http404):
                response = TestUpdateView.as_view()(request, slug='nonexistent')

    def test_alternate_declarations(self):
        'If no model is provided but there is a custom get_object, queryset should use it'
        class NoModelView(TranslatableUpdateView):
            def get_object(self, queryset=None):
                return Normal.objects.untranslated().get(pk=self.kwargs['pk'])
        request = self.request_factory.get('/url/')
        request.user = self.user
        response = NoModelView.as_view()(request, pk=self.normal_id[1])
        self.assertEqual(response.status_code, 200)
        data = response.context_data['form'].initial
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(data['translated_field'], NORMAL[1].translated_field['en'])

    def test_post_default(self):
        'Update an object with default language'

        # Valid form, existing translation
        with LanguageOverride('en'):
            request = self.request_factory.post('/url/', data={
                'shared_field': 'shared',
                'translated_field': 'translated',
            })
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[1])
            self.assertEqual(response.status_code, 302)
            self.assertEqual(int(response['Location']), self.normal_id[1])
            obj = Normal.objects.language('en').get(pk=self.normal_id[1])
            self.assertEqual(obj.shared_field, 'shared')
            self.assertEqual(obj.translated_field, 'translated')


        # Valid form, nonexisting translation
        with LanguageOverride('sr'):
            request = self.request_factory.post('/url/', data={
                'shared_field': 'shared-bis',
                'translated_field': 'translated-bis',
            })
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[1])
            self.assertEqual(response.status_code, 302)
            self.assertEqual(int(response['Location']), self.normal_id[1])
            obj = Normal.objects.language('sr').get(pk=self.normal_id[1])
            self.assertEqual(obj.shared_field, 'shared-bis')
            self.assertEqual(obj.translated_field, 'translated-bis')

        # Invalid form
        with LanguageOverride('en'):
            request = self.request_factory.post('/url/', data={
                'shared_field': 'shared',
                'translated_field': 'x'*999,
            })
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[2])
            self.assertEqual(response.status_code, 200)
            obj = Normal.objects.language('en').get(pk=self.normal_id[2])
            self.assertEqual(obj.shared_field, NORMAL[2].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[2].translated_field['en'])

    def test_post_language(self):
        'Update an object with default language'
        with LanguageOverride('en'):
            # Valid form, existing translation
            request = self.request_factory.post('/url/?language=ja', data={
                'shared_field': 'shared',
                'translated_field': 'translated',
            })
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[1])
            self.assertEqual(response.status_code, 302)
            self.assertEqual(int(response['Location']), self.normal_id[1])
            obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
            self.assertEqual(obj.shared_field, 'shared')
            self.assertEqual(obj.translated_field, 'translated')


            # Valid form, nonexisting translation
            request = self.request_factory.post('/url/?language=sr', data={
                'shared_field': 'shared-bis',
                'translated_field': 'translated-bis',
            })
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[1])
            self.assertEqual(response.status_code, 302)
            self.assertEqual(int(response['Location']), self.normal_id[1])
            obj = Normal.objects.language('sr').get(pk=self.normal_id[1])
            self.assertEqual(obj.shared_field, 'shared-bis')
            self.assertEqual(obj.translated_field, 'translated-bis')

            # Invalid form
            request = self.request_factory.post('/url/?language=ja', data={
                'shared_field': 'shared',
                'translated_field': 'x'*999,
            })
            request.user = self.user
            response = TestUpdateView.as_view()(request, pk=self.normal_id[2])
            self.assertEqual(response.status_code, 200)
            obj = Normal.objects.language('ja').get(pk=self.normal_id[2])
            self.assertEqual(obj.shared_field, NORMAL[2].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[2].translated_field['ja'])


class TransitionTests(HvadTestCase, NormalFixture):
    normal_count = 1

    def setUp(self):
        super(TransitionTests, self).setUp()
        self.user = User.objects.create(username='admin', is_superuser=True)

    def test__get_object_deprecation(self):
        with LanguageOverride('en'):
            request = self.request_factory.get('/url/')
            request.user = self.user

            with self.assertThrowsWarning(DeprecationWarning):
                response = DeprecatedObjectUpdateView.as_view()(request, pk=self.normal_id[1])

            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertEqual(data['translated_field'], NORMAL[1].translated_field['en'])

    def test_filter_kwargs_deprecation(self):
        with LanguageOverride('en'):
            request = self.request_factory.get('/url/')
            request.user = self.user

            with self.assertThrowsWarning(DeprecationWarning):
                response = DeprecatedFilterUpdateView.as_view()(request, custom=NORMAL[1].shared_field)

            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertEqual(data['translated_field'], NORMAL[1].translated_field['en'])

    def test_object_id_deprecation(self):
        with LanguageOverride('en'):
            request = self.request_factory.get('/url/')
            request.user = self.user

            with self.assertThrowsWarning(DeprecationWarning):
                response = TestUpdateView.as_view()(request, object_id=self.normal_id[1])

            self.assertEqual(response.status_code, 200)
            data = response.context_data['form'].initial
            self.assertEqual(data['id'], self.normal_id[1])
            self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
            self.assertEqual(data['translated_field'], NORMAL[1].translated_field['en'])

    def test__language_deprecation(self):
        request = self.request_factory.get('/url/?lang=ja')
        request.user = self.user

        with self.assertThrowsWarning(DeprecationWarning):
            response = DeprecatedLanguageUpdateView.as_view()(request, pk=self.normal_id[1])

        self.assertEqual(response.status_code, 200)
        data = response.context_data['form'].initial
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(data['translated_field'], NORMAL[1].translated_field['ja'])

    def test_context_modifiers_deprecation(self):
        with LanguageOverride('en'):
            request = self.request_factory.get('/url/')
            request.user = self.user

            with self.assertThrowsWarning(DeprecationWarning):
                response = DeprecatedContextUpdateView.as_view()(request, pk=self.normal_id[1])

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['modifier'], 'foo')

    def test_translatable_base_deprecation(self):
        from hvad.views import TranslatableBaseView
        with self.assertThrowsWarning(DeprecationWarning):
            TranslatableBaseView()
