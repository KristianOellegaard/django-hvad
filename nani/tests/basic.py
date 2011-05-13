# -*- coding: utf-8 -*-
from __future__ import with_statement
from django.core.exceptions import ImproperlyConfigured
from django.db.models.manager import Manager
from django.db.models.query_utils import Q
from nani.manager import TranslationManager
from nani.models import TranslatableModelBase, TranslatableModel 
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.data import DOUBLE_NORMAL
from nani.test_utils.testcase import NaniTestCase, SingleNormalTestCase
from testproject.app.models import Normal


class InvalidModel2(object):
    objects = TranslationManager()


class DefinitionTests(NaniTestCase):
    def test_invalid_manager(self):
        attrs = {
            'objects': Manager(),
            '__module__': 'testproject.app',
        }
        self.assertRaises(ImproperlyConfigured, TranslatableModelBase,
                          'InvalidModel', (TranslatableModel,), attrs)
    
    def test_no_translated_fields(self):
        attrs = dict(InvalidModel2.__dict__)
        del attrs['__dict__']
        bases = (TranslatableModel,InvalidModel2,)
        self.assertRaises(ImproperlyConfigured, TranslatableModelBase,
                          'InvalidModel2', bases, attrs)


class OptionsTest(NaniTestCase):
    def test_options(self):
        opts = Normal._meta
        self.assertTrue(hasattr(opts, 'translations_model'))
        self.assertTrue(hasattr(opts, 'translations_accessor'))
        relmodel = Normal._meta.get_field_by_name(opts.translations_accessor)[0].model
        self.assertEqual(relmodel, opts.translations_model)


class CreateTest(NaniTestCase):
    def test_create(self):
        with self.assertNumQueries(2):
            en = Normal.objects.language('en').create(
                shared_field="shared",
                translated_field='English',
            )
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
    
    def test_invalid_instantiation(self):
        self.assertRaises(RuntimeError, Normal, master=None)
    
    def test_create_nolang(self):
        with self.assertNumQueries(2):
            with LanguageOverride('en'):
                en = Normal.objects.create(
                    shared_field="shared",
                    translated_field='English',
                )
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
    
    def test_create_instance_simple(self):
        obj = Normal(language_code='en')
        obj.shared_field = "shared"
        obj.translated_field = "English"
        obj.save()
        en = Normal.objects.language('en').get(pk=obj.pk)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
        
    def test_create_instance_shared(self):
        obj = Normal(language_code='en', shared_field = "shared")
        obj.save()
        en = Normal.objects.language('en').get(pk=obj.pk)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.language_code, "en")
        
    def test_create_instance_translated(self):
        obj = Normal(language_code='en', translated_field = "English")
        obj.save()
        en = Normal.objects.language('en').get(pk=obj.pk)
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
    
    def test_create_instance_both(self):
        obj = Normal(language_code='en', shared_field = "shared",
                     translated_field = "English")
        obj.save()
        en = Normal.objects.language('en').get(pk=obj.pk)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
        
    def test_create_instance_simple_nolang(self):
        with LanguageOverride('en'):
            obj = Normal(language_code='en')
            obj.shared_field = "shared"
            obj.translated_field = "English"
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.shared_field, "shared")
            self.assertEqual(en.translated_field, "English")
            self.assertEqual(en.language_code, "en")
        
    def test_create_instance_shared_nolang(self):
        with LanguageOverride('en'):
            obj = Normal(language_code='en', shared_field = "shared")
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.shared_field, "shared")
            self.assertEqual(en.language_code, "en")
        
    def test_create_instance_translated_nolang(self):
        with LanguageOverride('en'):
            obj = Normal(language_code='en', translated_field = "English")
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.translated_field, "English")
            self.assertEqual(en.language_code, "en")
    
    def test_create_instance_both_nolang(self):
        with LanguageOverride('en'):
            obj = Normal(language_code='en', shared_field = "shared",
                         translated_field = "English")
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.shared_field, "shared")
            self.assertEqual(en.translated_field, "English")
            self.assertEqual(en.language_code, "en")


class TranslatedTest(SingleNormalTestCase):
    def test_translate(self):
        SHARED_EN = 'shared'
        TRANS_EN = 'English'
        SHARED_JA = 'shared'
        TRANS_JA = u'日本語'
        en = self.get_obj()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 1)
        self.assertEqual(en.shared_field, SHARED_EN)
        self.assertEqual(en.translated_field, TRANS_EN)
        ja = en
        ja.translate('ja')
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        self.assertEqual(ja.shared_field, SHARED_JA)
        self.assertEqual(ja.translated_field, '')
        ja.translated_field = TRANS_JA
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        self.assertEqual(ja.shared_field, SHARED_JA)
        self.assertEqual(ja.translated_field, TRANS_JA)
        with LanguageOverride('en'):
            obj = self.reload(ja)
            self.assertEqual(obj.shared_field, SHARED_EN)
            self.assertEqual(obj.translated_field, TRANS_EN)
        with LanguageOverride('ja'):
            obj = self.reload(en)
            self.assertEqual(obj.shared_field, SHARED_JA)
            self.assertEqual(obj.translated_field, TRANS_JA)
        

class GetTest(SingleNormalTestCase):
    def test_get(self):
        en = self.get_obj()
        with self.assertNumQueries(1):
            got = Normal.objects.get(pk=en.pk, language_code='en')
        with self.assertNumQueries(0):
            self.assertEqual(got.shared_field, "shared")
            self.assertEqual(got.translated_field, "English")
            self.assertEqual(got.language_code, "en")
    
    def test_safe_translation_getter(self):
        untranslated = Normal.objects.untranslated().get(pk=1)
        with LanguageOverride('en'):
            self.assertEqual(untranslated.safe_translation_getter('translated_field', None), None)
            en = Normal.objects.untranslated().get(pk=1)
            self.assertEqual(untranslated.safe_translation_getter('translated_field', "English"), "English")
        with LanguageOverride('ja'):
            self.assertEqual(untranslated.safe_translation_getter('translated_field', None), None)
            self.assertEqual(untranslated.safe_translation_getter('translated_field', "Test"), "Test")
        


class GetByLanguageTest(NaniTestCase):
    fixtures = ['double_normal.json']
    
    def test_args(self):
        with LanguageOverride('en'):
            q = Q(language_code='ja', pk=1)
            obj = Normal.objects.get(q)
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])
    
    def test_kwargs(self):
        with LanguageOverride('en'):
            kwargs = {'language_code':'ja', 'pk':1}
            obj = Normal.objects.get(**kwargs)
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])
        
    def test_language(self):
        with LanguageOverride('en'):
            obj = Normal.objects.language('ja').get(pk=1)
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])


class BasicQueryTest(SingleNormalTestCase):
    def test_basic(self):
        en = self.get_obj()
        with self.assertNumQueries(1):
            queried = Normal.objects.language('en').get(pk=en.pk)
            self.assertEqual(queried.shared_field, en.shared_field)
            self.assertEqual(queried.translated_field, en.translated_field)
            self.assertEqual(queried.language_code, en.language_code)


class DeleteLanguageCodeTest(SingleNormalTestCase):
    def test_delete_language_code(self):
        en = self.get_obj()
        self.assertRaises(AttributeError, delattr, en, 'language_code')


class FallbackTest(NaniTestCase):
    fixtures = ['double_normal.json']
    def test_single_instance_fallback(self):
        # fetch an object in a language that does not exist
        with LanguageOverride('de'):
            obj = Normal.objects.untranslated().use_fallbacks('en', 'ja').get(pk=1)
            self.assertEqual(obj.language_code, 'en')
            self.assertEqual(obj.translated_field, 'English1')
    
    def test_shared_only(self):
        with LanguageOverride('de'):
            obj = Normal.objects.untranslated().get(pk=1)
            self.assertEqual(obj.shared_field, 'Shared1')
            self.assertRaises(Normal._meta.translations_model.DoesNotExist,
                              getattr, obj, 'translated_field')
                              
class DescriptorTests(NaniTestCase):
    def test_translated_attribute_set(self):
        # 'MyModel' should return the default field value, in case there is no translation
        from nani.models import TranslatedFields
        from django.db import models
        
        DEFAULT = 'world'
        class MyModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(default=DEFAULT, max_length=128)
            )
        self.assertEqual(MyModel.hello, DEFAULT)
    
    def test_translated_attribute_delete(self):    
        # Its not possible to delete the charfield, which should result in an AttributeError
        obj = Normal.objects.language("en").create(shared_field="test", translated_field="en")
        obj.save()
        self.assertEqual(obj.translated_field, "en")
        delattr(obj, 'translated_field')
        self.assertRaises(AttributeError, getattr, obj, 'translated_field')
    
    def test_languagecodeattribute(self):
        # Its not possible to set/delete a language code
        self.assertRaises(AttributeError, setattr, Normal(), 'language_code', "en")
        self.assertRaises(AttributeError, delattr, Normal(), 'language_code')
