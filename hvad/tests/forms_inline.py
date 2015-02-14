# -*- coding: utf-8 -*-
from django.forms import ModelForm
from django.utils import translation
from hvad.admin import TranslatableModelAdminMixin
from hvad.forms import translatable_inlineformset_factory, translationformset_factory
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, Related
from hvad.test_utils.fixtures import NormalFixture
from hvad.test_utils.data import NORMAL
from hvad.test_utils.forms import FormData


class TestBasicInline(HvadTestCase):
    def setUp(self):
        with translation.override("en"):
            self.object = Normal.objects.language().create(shared_field="test", translated_field="translated test")
            self.request = self.request_factory.post('/url/')

    def test_create_fields_inline(self):
        with translation.override("en"):
            # Fixtures (should eventually be shared with other tests)

            translate_mixin = TranslatableModelAdminMixin()
            formset = translatable_inlineformset_factory(translate_mixin._language(self.request),
                                                         Normal, Related)(#self.request.POST,
                                                                          instance=self.object)

            self.assertTrue("normal" in formset.forms[0].fields)
            self.assertTrue("translated" in formset.forms[0].fields)
            self.assertTrue("translated_to_translated" in formset.forms[0].fields)
            self.assertFalse("language_code" in formset.forms[0].fields)

class TestTranslationsInline(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_render_formset(self):
        instance = Normal.objects.language('en').get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            Formset = translationformset_factory(Normal, extra=1, exclude=[])
            formset = Formset(instance=instance)
            self.assertEqual(len(formset.forms), 3)
            self.assertIn('translated_field', formset.forms[0].fields)
            self.assertIn('language_code', formset.forms[0].fields)
            self.assertIn('DELETE', formset.forms[0].fields)
            self.assertIn('id', formset.forms[0].fields)
            self.assertNotIn('master', formset.forms[0].fields)
            self.assertEqual(formset.forms[0].initial['language_code'], 'en')
            self.assertEqual(formset.forms[0].initial['translated_field'],
                             NORMAL[1].translated_field['en'])
            self.assertEqual(formset.forms[1].initial['language_code'], 'ja')
            self.assertEqual(formset.forms[1].initial['translated_field'],
                             NORMAL[1].translated_field['ja'])
            self.assertEqual(formset.forms[2].initial, {})

        with self.assertNumQueries(1):
            class Form(ModelForm):
                class Meta:
                    fields = ('translated_field',)
            Formset = translationformset_factory(Normal, form=Form, extra=1, exclude=[])
            formset = Formset(instance=instance)
            self.assertIn('translated_field', formset.forms[0].fields)
            self.assertIn('language_code', formset.forms[0].fields)
            self.assertIn('DELETE', formset.forms[0].fields)
            self.assertIn('id', formset.forms[0].fields)
            self.assertNotIn('master', formset.forms[0].fields)

    def test_create_translations(self):
        instance = Normal.objects.untranslated().get(pk=self.normal_id[1])
        Formset = translationformset_factory(Normal, extra=1, exclude=[])

        initial = Formset(instance=instance)
        data = FormData(initial)
        data.set_formset_field(initial, 2, 'language_code', 'de')
        data.set_formset_field(initial, 2, 'translated_field', 'Deutsch')

        formset = Formset(data=data, instance=instance)
        formset.save()

        obj = Normal.objects.language('de').get(pk=instance.pk)
        self.assertEqual(obj.translated_field, 'Deutsch')
        self.assertEqual(obj.translations.count(), 3)


    def test_delete_translations(self):
        instance = Normal.objects.language('en').get(pk=self.normal_id[1])
        Formset = translationformset_factory(Normal, extra=1, exclude=[])

        # Delete one of the two translations
        initial = Formset(instance=instance)
        data = FormData(initial)
        data.set_formset_field(initial, 0, 'DELETE', 'DELETE')

        formset = Formset(data=data, instance=instance)
        self.assertTrue(formset.is_valid())
        formset.save()

        self.assertCountEqual(instance.get_available_languages(), ('ja',))

        # Try to delete the other translation - should fail
        initial = Formset(instance=instance)
        data = FormData(initial)
        data.set_formset_field(initial, 0, 'DELETE', 'DELETE')

        formset = Formset(data=data, instance=instance)
        self.assertFalse(formset.is_valid())


    def test_mixed_update_translations(self):
        instance = Normal.objects.language('en').get(pk=self.normal_id[1])
        Formset = translationformset_factory(Normal, extra=1, exclude=[])

        initial = Formset(instance=instance)
        data = FormData(initial)
        data.set_formset_field(initial, 0, 'DELETE', 'DELETE')
        data.set_formset_field(initial, 1, 'translated_field', 'updated_ja')
        data.set_formset_field(initial, 2, 'language_code', 'de')
        data.set_formset_field(initial, 2, 'translated_field', 'Deutsch')

        formset = Formset(data=data, instance=instance)
        self.assertTrue(formset.is_valid())
        formset.save()

        self.assertCountEqual(instance.get_available_languages(), ('ja', 'de'))

        obj = Normal.objects.language('ja').get(pk=instance.pk)
        self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj.translated_field, 'updated_ja')

        obj = Normal.objects.language('de').get(pk=instance.pk)
        self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj.translated_field, 'Deutsch')
