# -*- coding: utf-8 -*-
from hvad.admin import TranslatableModelAdminMixin
from hvad.forms import translatable_inlineformset_factory, translationformset_factory
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import NaniTestCase
from hvad.test_utils.request_factory import RequestFactory
from hvad.test_utils.project.app.models import Normal, Related
from hvad.test_utils.forms import FormData


class TestBasicInline(NaniTestCase):
    def setUp(self):
        with LanguageOverride("en"):
            self.object = Normal.objects.language().create(shared_field="test", translated_field="translated test")
            rf = RequestFactory()
            self.request = rf.post('/url/')

    def test_create_fields_inline(self):
        with LanguageOverride("en"):
            # Fixtures (should eventually be shared with other tests)

            translate_mixin = TranslatableModelAdminMixin()
            formset = translatable_inlineformset_factory(translate_mixin._language(self.request),
                                                         Normal, Related)(#self.request.POST,
                                                                          instance=self.object)

            self.assertTrue("normal" in formset.forms[0].fields)
            self.assertTrue("translated" in formset.forms[0].fields)
            self.assertTrue("translated_to_translated" in formset.forms[0].fields)
            self.assertFalse("language_code" in formset.forms[0].fields)

class TestTranslationsInline(NaniTestCase):
    def setUp(self):
        with LanguageOverride('en'):
            self.object = Normal.objects.language().create(
                shared_field='test',
                translated_field='translated_test_en'
            )
            self.object.translate('fr')
            self.object.translated_field='translated_test_fr'
            self.object.save()

    def test_render_formset(self):
        with self.assertNumQueries(1):
            Formset = translationformset_factory(Normal, extra=1)
            formset = Formset(instance=self.object)
            self.assertEqual(len(formset.forms), 3)
            self.assertIn('translated_field', formset.forms[0].fields)
            self.assertIn('language_code', formset.forms[0].fields)
            self.assertIn('DELETE', formset.forms[0].fields)
            self.assertIn('id', formset.forms[0].fields)
            self.assertNotIn('master', formset.forms[0].fields)
            self.assertEqual(formset.forms[0].initial['language_code'], 'en')
            self.assertEqual(formset.forms[0].initial['translated_field'], 'translated_test_en')
            self.assertEqual(formset.forms[1].initial['language_code'], 'fr')
            self.assertEqual(formset.forms[1].initial['translated_field'], 'translated_test_fr')
            self.assertEqual(formset.forms[2].initial, {})

    def test_create_translations(self):
        Formset = translationformset_factory(Normal, extra=1)

        initial = Formset(instance=self.object)
        data = FormData(initial)
        data.set_formset_field(initial, 2, 'language_code', 'de')
        data.set_formset_field(initial, 2, 'translated_field', 'translated_test_de')

        formset = Formset(data=data, instance=self.object)
        formset.save()

        obj = Normal.objects.language('de').get(pk=self.object.pk)
        self.assertEqual(obj.translated_field, 'translated_test_de')
        self.assertEqual(obj.translations.count(), 3)


    def test_delete_translations(self):
        Formset = translationformset_factory(Normal, extra=1)

        # Delete one of the two translations
        initial = Formset(instance=self.object)
        data = FormData(initial)
        data.set_formset_field(initial, 0, 'DELETE', 'DELETE')

        formset = Formset(data=data, instance=self.object)
        self.assertTrue(formset.is_valid())
        formset.save()

        self.assertCountEqual(self.object.get_available_languages(), ('fr',))

        # Try to delete the other translation - should fail
        initial = Formset(instance=self.object)
        data = FormData(initial)
        data.set_formset_field(initial, 0, 'DELETE', 'DELETE')

        formset = Formset(data=data, instance=self.object)
        self.assertFalse(formset.is_valid())


    def test_mixed_update_translations(self):
        Formset = translationformset_factory(Normal, extra=1)

        initial = Formset(instance=self.object)
        data = FormData(initial)
        data.set_formset_field(initial, 0, 'DELETE', 'DELETE')
        data.set_formset_field(initial, 1, 'translated_field', 'updated_fr')
        data.set_formset_field(initial, 2, 'language_code', 'de')
        data.set_formset_field(initial, 2, 'translated_field', 'translated_test_de')

        formset = Formset(data=data, instance=self.object)
        self.assertTrue(formset.is_valid())
        formset.save()

        self.assertCountEqual(self.object.get_available_languages(), ('fr', 'de'))

        obj = Normal.objects.language('fr').get(pk=self.object.pk)
        self.assertEqual(obj.shared_field, 'test')
        self.assertEqual(obj.translated_field, 'updated_fr')

        obj = Normal.objects.language('de').get(pk=self.object.pk)
        self.assertEqual(obj.shared_field, 'test')
        self.assertEqual(obj.translated_field, 'translated_test_de')

