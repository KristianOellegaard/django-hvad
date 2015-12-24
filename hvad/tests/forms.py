# -*- coding: utf-8 -*-
from django.core.exceptions import FieldError
from django.utils import translation
from hvad.forms import (TranslatableModelForm,
                        translatable_modelform_factory, translatable_modelformset_factory)
from hvad.utils import get_cached_translation
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, SimpleRelated, Standard
from hvad.test_utils.data import NORMAL
from hvad.test_utils.fixtures import NormalFixture
from django import forms

#=============================================================================

class NormalForm(TranslatableModelForm):
    class Meta:
        model = Normal
        fields = ['shared_field', 'translated_field']

class NormalMediaForm(TranslatableModelForm):
    class Meta:
        model = Normal
        exclude = []
    class Media:
        css = {
            'all': ('layout.css',)
        }

class CustomLanguageNormalForm(NormalForm):
    def clean(self):
        data = super(CustomLanguageNormalForm, self).clean()
        data['seen_language'] = data.get('language_code')
        data['language_code'] = 'sr'
        return data

    class Meta:
        model = Normal
        fields = ['shared_field', 'translated_field']

class SimpleRelatedForm(TranslatableModelForm):
    normal = forms.ModelChoiceField(queryset=Normal.objects.language())
    class Meta:
        model = SimpleRelated
        fields = ['normal', 'translated_field']


#=============================================================================

class FormDeclarationTests(HvadTestCase):
    'Mostly metaclass and factory tests'

    def test_no_meta(self):
        'Empty form and filled in variant from factory'
        class Form(TranslatableModelForm):
            pass
        self.assertIs(Form._meta.fields, None)
        self.assertCountEqual(Form._meta.exclude, [])
        self.assertCountEqual(Form.base_fields, [])

        engineered = translatable_modelform_factory('en', Normal, form=Form)
        self.assertIs(Form._meta.fields, None)
        self.assertCountEqual(engineered._meta.exclude, ['translations'])
        self.assertCountEqual(engineered.base_fields, ['shared_field', 'translated_field'])

    def test_no_meta_inherits(self):
        'Auto-created meta inherits meta of first base class'
        class Form(TranslatableModelForm):
            class Meta:
                model = Normal
        class InheritedForm(Form):
            pass
        self.assertIsInstance(InheritedForm._meta, Form._meta.__class__)
        self.assertIs(InheritedForm._meta.model, Normal)

    def test_only_model(self):
        'Standalone form with model in Meta'
        class Form(TranslatableModelForm):
            class Meta:
                model = Normal
        self.assertIs(Form._meta.fields, None)
        self.assertCountEqual(Form._meta.exclude, ['translations'])
        self.assertCountEqual(Form.base_fields, ['shared_field', 'translated_field'])

    def test_only_fields(self):
        'Empty form and filled in variant from factory - applies field restriction'
        class Form(TranslatableModelForm):
            class Meta:
                fields = ('shared_field', 'translated_field')
        self.assertCountEqual(Form._meta.fields, ['shared_field', 'translated_field'])
        self.assertCountEqual(Form._meta.exclude, [])
        self.assertCountEqual(Form.base_fields, [])

        engineered = translatable_modelform_factory('en', Normal, form=Form)
        self.assertCountEqual(engineered._meta.fields, ['shared_field', 'translated_field'])
        self.assertCountEqual(engineered._meta.exclude, ['translations'])
        self.assertCountEqual(engineered.base_fields, ['shared_field', 'translated_field'])

    def test_fields_all(self):
        'Empty form and filled in variant from factory - using __all__ special value'
        class Form(TranslatableModelForm):
            class Meta:
                model = Normal
                fields = '__all__'
        self.assertIs(Form._meta.fields, None)
        self.assertCountEqual(Form._meta.exclude, ['translations'])
        self.assertCountEqual(Form.base_fields, ['shared_field', 'translated_field'])

        engineered = translatable_modelform_factory('en', Normal, form=Form)
        self.assertIs(engineered._meta.fields, None)
        self.assertCountEqual(engineered._meta.exclude, ['translations'])
        self.assertCountEqual(engineered.base_fields, ['shared_field', 'translated_field'])


    def test_model_and_fields(self):
        'Standalone form with model in Meta and field restrictions'
        class Form1(TranslatableModelForm):     # merged fields
            class Meta:
                model = Normal
                fields = ('shared_field', 'translated_field')
        self.assertCountEqual(Form1._meta.fields, ['shared_field', 'translated_field'])
        self.assertCountEqual(Form1._meta.exclude, ['translations'])
        self.assertCountEqual(Form1.base_fields, ['shared_field', 'translated_field'])

        class Form2(TranslatableModelForm):     # only shared fields
            class Meta:
                model = Normal
                fields = ('shared_field',)
        self.assertCountEqual(Form2._meta.fields, ['shared_field'])
        self.assertCountEqual(Form2._meta.exclude, ['translations'])
        self.assertCountEqual(Form2.base_fields, ['shared_field'])

        class Form3(TranslatableModelForm):     # only translated fields
            class Meta:
                model = Normal
                fields = ('translated_field',)
        self.assertCountEqual(Form3._meta.fields, ['translated_field'])
        self.assertCountEqual(Form3._meta.exclude, ['translations'])
        self.assertCountEqual(Form3.base_fields, ['translated_field'])

        with self.assertRaises(FieldError):     # invalid fields
            class Form4(TranslatableModelForm):
                class Meta:
                    model = Normal
                    fields = ('nonexistent',)

    def test_special_fields(self):
        'Special handling of master, language_code and translation accessor'
        # language_code is a reserved field name
        with self.assertRaises(FieldError):
            class Form1(TranslatableModelForm):
                class Meta:
                    fields = ('shared_model', 'language_code')
        # translation accessor would wreak havoc on the model
        with self.assertRaises(FieldError):
            class Form2(TranslatableModelForm):
                class Meta:
                    model = Normal
                    fields = ('shared_mode', Normal._meta.translations_accessor)
        # master is a valid shared field, but translation's master should be concealed
        with self.assertRaises(FieldError):
            class Form3(TranslatableModelForm):
                class Meta:
                    model = Normal
                    fields = ('shared_model', 'master')

    def test_invalid(self):
        'Check that TranslatableModelForm does not accept invalid arguments'
        self.assertRaises(TypeError, translatable_modelform_factory, 'en', Standard)
        self.assertRaises(TypeError, translatable_modelform_factory, 'en', Normal,
                          form=forms.ModelForm)

#=============================================================================

class FormInstantiationTests(HvadTestCase, NormalFixture):
    'Form initialization and rendering from instance and initial data'
    normal_count = 2

    def test_empty(self):
        form = NormalForm()
        self.assertCountEqual(form.fields, ['shared_field', 'translated_field'])
        self.assertFalse(form.is_valid())
        self.assertRaises(AssertionError, form.save)

        form = NormalMediaForm()
        self.assertCountEqual(form.fields, ['shared_field', 'translated_field'])
        self.assertFalse(form.is_valid())
        self.assertIn('layout.css', str(form.media))

    def test_simple_related_form(self):
        with translation.override('en'):
            form = SimpleRelatedForm()
            rendered = form['normal'].as_widget()
            for index in self.normal_id:
                self.assertIn(NORMAL[index].translated_field['en'], rendered)

        with translation.override('ja'):
            form = SimpleRelatedForm()
            rendered = form['normal'].as_widget()
            for index in self.normal_id:
                self.assertIn(NORMAL[index].translated_field['ja'], rendered)

    def test_instance(self):
        # no language enforced
        with self.assertNumQueries(1):
            form = NormalForm(instance=Normal.objects.language('ja').get(pk=self.normal_id[1]))
        self.assertFalse(form.is_valid())
        self.assertCountEqual(form.initial, ['shared_field', 'translated_field'])
        self.assertEqual(form.initial['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(form.initial['translated_field'], NORMAL[1].translated_field['ja'])
        self.assertIn('value="%s"' % NORMAL[1].shared_field, form.as_p())
        self.assertIn('value="%s"' % NORMAL[1].translated_field['ja'], form.as_p())
        self.assertEqual(get_cached_translation(form.instance).language_code, 'ja')

        # enforce japanese language
        with self.assertNumQueries(1):
            Form = translatable_modelform_factory('ja', Normal, form=NormalForm)
            form = Form(instance=Normal.objects.language('ja').get(pk=self.normal_id[1]))
        self.assertFalse(form.is_valid())
        self.assertCountEqual(form.initial, ['shared_field', 'translated_field'])
        self.assertEqual(form.initial['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(form.initial['translated_field'], NORMAL[1].translated_field['ja'])
        self.assertIn('value="%s"' % NORMAL[1].shared_field, form.as_p())
        self.assertIn('value="%s"' % NORMAL[1].translated_field['ja'], form.as_p())
        self.assertEqual(get_cached_translation(form.instance).language_code, 'ja')

    def test_instance_untranslated(self):
        # no language enforced, should load anyway
        with translation.override('en'):
            form = NormalForm(instance=Normal.objects.untranslated().get(pk=self.normal_id[1]))
        self.assertFalse(form.is_valid())
        self.assertCountEqual(form.initial, ['shared_field', 'translated_field'])
        self.assertEqual(form.initial['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(form.initial['translated_field'], NORMAL[1].translated_field['en'])
        self.assertIn('value="%s"' % NORMAL[1].shared_field, form.as_p())
        self.assertIn('value="%s"' % NORMAL[1].translated_field['en'], form.as_p())
        self.assertIs(get_cached_translation(form.instance), None)

        # enforce japanese language
        with translation.override('en'):
            Form = translatable_modelform_factory('ja', Normal, form=NormalForm)
            form = Form(instance=Normal.objects.untranslated().get(pk=self.normal_id[1]))
        self.assertFalse(form.is_valid())
        self.assertCountEqual(form.initial, ['shared_field', 'translated_field'])
        self.assertEqual(form.initial['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(form.initial['translated_field'], NORMAL[1].translated_field['ja'])
        self.assertIn('value="%s"' % NORMAL[1].shared_field, form.as_p())
        self.assertIn('value="%s"' % NORMAL[1].translated_field['ja'], form.as_p())
        self.assertIs(get_cached_translation(form.instance), None)

    def test_instance_wrong_translation(self):
        # no language enforced
        form = NormalForm(instance=Normal.objects.language('en').get(pk=self.normal_id[1]))
        self.assertFalse(form.is_valid())
        self.assertCountEqual(form.initial, ['shared_field', 'translated_field'])
        self.assertEqual(form.initial['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(form.initial['translated_field'], NORMAL[1].translated_field['en'])
        self.assertIn('value="%s"' % NORMAL[1].shared_field, form.as_p())
        self.assertIn('value="%s"' % NORMAL[1].translated_field['en'], form.as_p())
        self.assertEqual(get_cached_translation(form.instance).language_code, 'en')

        # enforce japanese language
        Form = translatable_modelform_factory('ja', Normal, form=NormalForm)
        form = Form(instance=Normal.objects.language('en').get(pk=self.normal_id[1]))
        self.assertFalse(form.is_valid())
        self.assertCountEqual(form.initial, ['shared_field', 'translated_field'])
        self.assertEqual(form.initial['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(form.initial['translated_field'], NORMAL[1].translated_field['ja'])
        self.assertIn('value="%s"' % NORMAL[1].shared_field, form.as_p())
        self.assertIn('value="%s"' % NORMAL[1].translated_field['ja'], form.as_p())
        self.assertEqual(get_cached_translation(form.instance).language_code, 'en')

    def test_instance_initial(self):
        Form = translatable_modelform_factory('ja', Normal, form=NormalForm)
        initial = {
            'shared_field': 'shared_initial',
            'translated_field': 'translated_initial',
        }
        form = Form(instance=Normal.objects.language('ja').get(pk=self.normal_id[1]),
                    initial=initial)
        self.assertFalse(form.is_valid())
        self.assertCountEqual(form.initial, ['shared_field', 'translated_field'])
        self.assertEqual(form.initial['shared_field'], 'shared_initial')
        self.assertEqual(form.initial['translated_field'], 'translated_initial')


#=============================================================================

class FormValidationTests(HvadTestCase, NormalFixture):
    'Testing form cleaning, especially the language_code with various settings'
    normal_count = 1

    def test_basic(self):
        'Basic form with data, should validate and set cleaned_data'
        data = {
            'shared_field': 'shared',
            'translated_field': 'English',
        }
        form = NormalForm(data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertCountEqual(form.cleaned_data, ['shared_field', 'translated_field'])
        self.assertEqual(form.cleaned_data['shared_field'], 'shared')
        self.assertEqual(form.cleaned_data['translated_field'], 'English')

    def test_instance(self):
        'Having an instance attached should not prevent normal working of the form'
        data = {
            'shared_field': 'shared',
            'translated_field': 'English',
        }
        form = NormalForm(data, instance=Normal.objects.language('en').get(pk=self.normal_id[1]))
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertCountEqual(form.cleaned_data, ['shared_field', 'translated_field'])
        self.assertEqual(form.cleaned_data['shared_field'], 'shared')
        self.assertEqual(form.cleaned_data['translated_field'], 'English')

    def test_language_code_not_enforcing(self):
        'Language code is not a field, it should not be in cleaned data by default'
        data = {
            'shared_field': 'shared',
            'translated_field': 'Japanese',
            'language_code': 'ja',
        }
        form = NormalForm(data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertCountEqual(form.cleaned_data, ['shared_field', 'translated_field'])

        form = CustomLanguageNormalForm(data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertCountEqual(form.cleaned_data, ['shared_field', 'translated_field',
                                                  'seen_language', 'language_code'])
        self.assertIs(form.cleaned_data['seen_language'], None)
        self.assertEqual(form.cleaned_data['language_code'], 'sr')

    def test_language_code_enforcing(self):
        'With language_code enforcing, language should be set automatically'
        Form = translatable_modelform_factory('ja', Normal, form=NormalForm)
        data = {
            'shared_field': 'shared',
            'translated_field': 'Japanese',
        }
        form = Form(data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertCountEqual(form.cleaned_data, ['shared_field', 'translated_field', 'language_code'])
        self.assertEqual(form.cleaned_data['language_code'], 'ja')

        data = {
            'shared_field': 'shared',
            'translated_field': 'Japanese',
            'language_code': 'sr',
        }
        Form = translatable_modelform_factory('ja', Normal, form=NormalForm)
        form = Form(data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertCountEqual(form.cleaned_data, ['shared_field', 'translated_field', 'language_code'])
        self.assertEqual(form.cleaned_data['language_code'], 'ja')

    def test_language_code_enforcing_override(self):
        'Custom clean() method should see language_code and be able to override it'
        Form = translatable_modelform_factory('ja', Normal, form=CustomLanguageNormalForm)
        data = {
            'shared_field': 'shared',
            'translated_field': 'Japanese',
        }
        form = Form(data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertCountEqual(form.cleaned_data, ['shared_field', 'translated_field',
                                                  'seen_language', 'language_code'])
        self.assertIs(form.cleaned_data['seen_language'], 'ja')
        self.assertEqual(form.cleaned_data['language_code'], 'sr')


#=============================================================================

class FormCommitTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_create_not_enforcing(self):
        'Calling save on a new instance with no language_code in cleaned_data'
        data = {
            'shared_field': 'shared',
            'translated_field': u'српски',
        }
        # no instance, should use current language
        with translation.override('sr'):
            form = NormalForm(data)
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertNotEqual(obj.pk, None)
                self.assertEqual(obj.language_code, 'sr')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, u'српски')

        # an instance with a translation loaded, should use that
        with translation.override('en'):
            form = NormalForm(data, instance=Normal(language_code='sr'))
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertNotEqual(obj.pk, None)
                self.assertEqual(obj.language_code, 'sr')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, u'српски')

    def test_create_enforcing(self):
        'Calling save() on a new instance with a language_code in cleaned_data'
        Form = translatable_modelform_factory('ja', Normal, form=NormalForm)
        data = {
            'shared_field': 'shared',
            'translated_field': 'Japanese',
        }
        with translation.override('en'):
            form = Form(data, instance=Normal(language_code='sr'))
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertNotEqual(obj.pk, None)
                self.assertEqual(obj.language_code, 'ja')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, 'Japanese')

    def test_update_not_enforcing(self):
        'Calling save on an existing instance with no language_code in cleaned_data'
        data = {
            'shared_field': 'shared',
            'translated_field': 'translated',
        }
        with translation.override('en'):
            # translation is loaded, use it
            form = NormalForm(data, instance=Normal.objects.language('ja').get(pk=self.normal_id[1]))
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertEqual(obj.pk, self.normal_id[1])
                self.assertEqual(obj.language_code, 'ja')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, 'translated')
            self.assertEqual(Normal.objects.language('ja').get(pk=self.normal_id[1]).translated_field,
                             'translated')

            # no translation loaded, use current language
            form = NormalForm(data, instance=Normal.objects.untranslated().get(pk=self.normal_id[1]))
            with self.assertNumQueries(3):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertEqual(obj.pk, self.normal_id[1])
                self.assertEqual(obj.language_code, 'en')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, 'translated')
            self.assertEqual(Normal.objects.language('en').get(pk=self.normal_id[1]).translated_field,
                             'translated')

            # new translation is loaded, use it
            obj.translate('sr')
            form = NormalForm(data, instance=obj)
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertEqual(obj.pk, self.normal_id[1])
                self.assertEqual(obj.language_code, 'sr')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, 'translated')
            self.assertEqual(Normal.objects.language('sr').get(pk=self.normal_id[1]).translated_field,
                             'translated')

    def test_update_enforcing(self):
        'Calling save on an existing instance, with a language_code in cleaned_data'
        Form = translatable_modelform_factory('sr', Normal, form=NormalForm)
        data = {
            'shared_field': 'shared',
            'translated_field': u'српски',
        }
        with translation.override('en'):
            # wrong translation is loaded, override it
            form = Form(data, instance=Normal.objects.language('ja').get(pk=self.normal_id[1]))
            with self.assertNumQueries(3):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertEqual(obj.pk, self.normal_id[1])
                self.assertEqual(obj.language_code, 'sr')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, u'српски')
            self.assertEqual(Normal.objects.language('sr').get(pk=self.normal_id[1]).translated_field,
                             u'српски')

    def test_set_fields_before_save(self):
        'Manually set some translated fields before calling save()'
        Form = translatable_modelform_factory('sr', Normal, form=NormalForm,
                                              exclude=['translated_field'])
        data = {
            'shared_field': 'shared',
        }
        with translation.override('en'):
            form = Form(data, instance=Normal.objects.language('ja').get(pk=self.normal_id[1]))
            with self.assertNumQueries(1):
                self.assertTrue(form.is_valid())
            form.instance.translated_field = u'ћирилица'
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertEqual(obj.pk, self.normal_id[1])
                self.assertEqual(obj.language_code, 'sr')
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, u'ћирилица')
            self.assertEqual(Normal.objects.language('sr').get(pk=self.normal_id[1]).translated_field,
                             u'ћирилица')

    def test_nocommit(self):
        'The commit=False should be properly honored'
        with translation.override('en'):
            data = {
                'shared_field': 'shared',
                'translated_field': 'English',
            }
            form = NormalForm(data)
            with self.assertNumQueries(0):
                obj = form.save(commit=False)
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, 'English')
                self.assertIs(obj.pk, None)
            with self.assertNumQueries(2):
                obj.save()
                self.assertEqual(obj.shared_field, 'shared')
                self.assertEqual(obj.translated_field, 'English')
                self.assertIsNot(obj.pk, None)


#=============================================================================

class FormsetTests(HvadTestCase, NormalFixture):
    'Very light parameter passing tests as we just forward calls to Django'
    normal_count = 0

    def test_create_formset(self):
        kwargs = {
            'form': NormalForm,
            'extra': 1,
            'can_delete': True,
            'can_order': False,
            'max_num': 5,
            'fields': ('translated_field',)
        }
        kwargs['validate_max'] = True
        kwargs['labels'] = {
            'shared_field': 'Shared Field',
            'translated_field': 'Translated Field',
        }
        kwargs['help_texts'] = {
            'shared_field': 'This is a field shared amongst languages',
            'translated_field': 'This field is specific to a language',
        }
        kwargs['localized_fields'] = ['translated_field']
        formset = translatable_modelformset_factory('en', Normal, **kwargs)
        self.assertTrue(issubclass(formset.form, NormalForm))

    def test_unknown_argument(self):
        self.assertRaises(TypeError, translatable_modelformset_factory,
                          'en', Normal, nonexistent='dummy')
