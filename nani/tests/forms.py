# -*- coding: utf-8 -*-
from nani.forms import TranslateableModelForm, TranslateableModelFormMetaclass
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal
from django.db import models

class NormalForm(TranslateableModelForm):
    class Meta:
        model = Normal

class FormTests(NaniTestCase):
    
    def test_nontranslatablemodelform(self):
        # Make sure that TranslateableModelForm won't accept a regular model
        
        # "Fake" model to use for the TranslateableModelForm
        class NonTranslatableModel(models.Model):
            field = models.CharField(max_length=128)
        # Meta class for use below
        class Meta:
            model = NonTranslatableModel
        # Make sure we do indeed get an exception, if we try to initialise it
        self.assertRaises(TypeError,
            TranslateableModelFormMetaclass,
            'NonTranslateableModelForm', (TranslateableModelForm,),
            {'Meta': Meta}
        )
    
    def test_normal_model_form_instantiation(self):
        form = NormalForm()
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
            with self.assertNumQueries(2):
                obj = form.save()
            with self.assertNumQueries(0):
                self.assertEqual(obj.shared_field, SHARED)
            with self.assertNumQueries(0):
                self.assertEqual(obj.translated_field, TRANSLATED)
            with self.assertNumQueries(0):
                self.assertNotEqual(obj.pk, None)