# -*- coding: utf-8 -*-
from django.core.exceptions import FieldError
from hvad.forms import TranslatableModelForm, TranslatableModelFormMetaclass
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal
from django.db import models

class NormalForm(TranslatableModelForm):
    class Meta:
        model = Normal
        fields = ['shared_field', 'translated_field']

class NormalMediaForm(TranslatableModelForm):
    class Meta:
        model = Normal
    class Media:
        css = {
            'all': ('layout.css',)
        }

class NormalFormExclude(TranslatableModelForm):
    class Meta:
        model = Normal
        exclude = ['shared_field']

class FormTests(NaniTestCase):
    
    def test_nontranslatablemodelform(self):
        # Make sure that TranslatableModelForm won't accept a regular model
        
        # "Fake" model to use for the TranslatableModelForm
        class NonTranslatableModel(models.Model):
            field = models.CharField(max_length=128)
        # Meta class for use below
        class Meta:
            model = NonTranslatableModel
        # Make sure we do indeed get an exception, if we try to initialise it
        self.assertRaises(TypeError,
            TranslatableModelFormMetaclass,
            'NonTranslatableModelForm', (TranslatableModelForm,),
            {'Meta': Meta}
        )
    
    def test_normal_model_form_instantiation(self):
        # Basic example and checking it gives us all the fields needed
        form = NormalForm()
        self.assertTrue("translated_field" in form.fields)
        self.assertTrue("shared_field" in form.fields)
        self.assertTrue("translated_field" in form.base_fields)
        self.assertTrue("shared_field" in form.base_fields)
        self.assertFalse(form.is_valid())
        
        # Check if it works with media argument too
        form = NormalMediaForm()
        self.assertFalse(form.is_valid())
        self.assertTrue("layout.css" in str(form.media))
        
        # Check if it works with an instance of Normal
        form = NormalForm(instance=Normal())
        self.assertFalse(form.is_valid())
        
        
    def test_normal_model_form_valid(self):
        SHARED = 'Shared'
        TRANSLATED = 'English'
        data = {
            'shared_field': SHARED,
            'translated_field': TRANSLATED,
            'language_code': 'en'
        }
        form = NormalForm(data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertTrue("translated_field" in form.fields)
        self.assertTrue("shared_field" in form.fields)
        self.assertTrue(TRANSLATED in form.clean()["translated_field"])
        self.assertTrue(SHARED in form.clean()["shared_field"])
        
    def test_normal_model_form_initaldata_instance(self):
        # Check if it accepts inital data and instance
        SHARED = 'Shared'
        TRANSLATED = 'English'
        data = {
            'shared_field': SHARED,
            'translated_field': TRANSLATED,
            'language_code': 'en'
        }
        form = NormalForm(data, instance=Normal(), initial=data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        
    def test_normal_model_form_existing_instance(self):
        # Check if it works with an existing instance of Normal
        SHARED = 'Shared'
        TRANSLATED = 'English'
        instance = Normal.objects.language("en").create(shared_field=SHARED, translated_field=TRANSLATED)
        form = NormalForm(instance=instance)
        self.assertFalse(form.is_valid())
        self.assertTrue(SHARED in form.as_p())
        self.assertTrue(TRANSLATED in form.as_p())
        
    
    def test_normal_model_form_save(self):
        with LanguageOverride('en'):
            SHARED = 'Shared'
            TRANSLATED = 'English'
            data = {
                'shared_field': SHARED,
                'translated_field': TRANSLATED,
                'language_code': 'en'
            }
            form = NormalForm(data)
            # tested a non-translated ModelForm, and that takes 7 queries.
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertEqual(obj.shared_field, SHARED)
                self.assertEqual(obj.translated_field, TRANSLATED)
                self.assertNotEqual(obj.pk, None)

    def test_no_language_code_in_fields(self):
        with LanguageOverride("en"):
            form = NormalForm()
            self.assertFalse(form.fields.has_key("language_code"))

            form = NormalMediaForm()
            self.assertFalse(form.fields.has_key("language_code"))

            form = NormalFormExclude()
            self.assertFalse(form.fields.has_key("language_code"))

    def test_form_wrong_field_in_class(self):
        with LanguageOverride("en"):            
            def create_wrong_form():
                class WrongForm(TranslatableModelForm):
                    class Meta:
                        model = Normal
                        fields = ['a_field_that_doesnt_exist']

                form = WrongForm()
            self.assertRaises(FieldError, create_wrong_form)
