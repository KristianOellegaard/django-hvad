# -*- coding: utf-8 -*-
from __future__ import with_statement
from django.core.exceptions import ImproperlyConfigured
from django.db.models.manager import Manager
from django.db.models.query_utils import Q
from hvad.manager import TranslationManager
from hvad.models import TranslatableModelBase, TranslatableModel
from hvad.test_utils.context_managers import LanguageOverride, SettingsOverride
from hvad.test_utils.data import DOUBLE_NORMAL
from hvad.test_utils.fixtures import (OneSingleTranslatedNormalMixin, 
    TwoTranslatedNormalMixin)
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal, MultipleFields
from testproject.alternate_models_app.models import NormalAlternate

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
        del attrs['__weakref__']
        bases = (TranslatableModel,InvalidModel2,)
        self.assertRaises(ImproperlyConfigured, TranslatableModelBase,
                          'InvalidModel2', bases, attrs)
    
    def test_abstract_base_model(self):
        class Meta:
            abstract = True
        attrs = {
            'Meta': Meta,
            '__module__': 'testproject.app',
        }
        model = TranslatableModelBase('MyBaseModel', (TranslatableModel,), attrs)
        self.assertTrue(model._meta.abstract)


class OptionsTest(NaniTestCase):
    def test_options(self):
        opts = Normal._meta
        self.assertTrue(hasattr(opts, 'translations_model'))
        self.assertTrue(hasattr(opts, 'translations_accessor'))
        relmodel = Normal._meta.get_field_by_name(opts.translations_accessor)[0].model
        self.assertEqual(relmodel, opts.translations_model)


class AlternateCreateTest(NaniTestCase):
    def test_create_instance_simple(self):
        obj = NormalAlternate(language_code='en')
        obj.shared_field = "shared"
        obj.translated_field = "English"
        obj.save()
        en = NormalAlternate.objects.language('en').get(pk=obj.pk)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
    

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


class TranslatedTest(NaniTestCase, OneSingleTranslatedNormalMixin):
    def test_translate(self):
        SHARED_EN = 'shared'
        TRANS_EN = 'English'
        SHARED_JA = 'shared'
        TRANS_JA = u'日本語'
        en = Normal.objects.language('en').get(pk=1)
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
        

class GetTest(NaniTestCase, OneSingleTranslatedNormalMixin):
    def test_get(self):
        en = Normal.objects.language('en').get(pk=1)
        with self.assertNumQueries(1):
            got = Normal.objects.using_translations().get(pk=en.pk, language_code='en')
        with self.assertNumQueries(0):
            self.assertEqual(got.shared_field, "shared")
            self.assertEqual(got.translated_field, "English")
            self.assertEqual(got.language_code, "en")
    
    def test_safe_translation_getter(self):
        untranslated = Normal.objects.untranslated().get(pk=1)
        with LanguageOverride('en'):
            self.assertEqual(untranslated.safe_translation_getter('translated_field', None), None)
            Normal.objects.untranslated().get(pk=1)
            self.assertEqual(untranslated.safe_translation_getter('translated_field', "English"), "English")
        with LanguageOverride('ja'):
            self.assertEqual(untranslated.safe_translation_getter('translated_field', None), None)
            self.assertEqual(untranslated.safe_translation_getter('translated_field', "Test"), "Test")
        


class GetByLanguageTest(NaniTestCase, TwoTranslatedNormalMixin):
    
    def test_args(self):
        with LanguageOverride('en'):
            q = Q(language_code='ja', pk=1)
            obj = Normal.objects.using_translations().get(q)
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])
    
    def test_kwargs(self):
        with LanguageOverride('en'):
            kwargs = {'language_code':'ja', 'pk':1}
            obj = Normal.objects.using_translations().get(**kwargs)
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])
        
    def test_language(self):
        with LanguageOverride('en'):
            obj = Normal.objects.language('ja').get(pk=1)
            self.assertEqual(obj.shared_field, DOUBLE_NORMAL[1]['shared_field'])
            self.assertEqual(obj.translated_field, DOUBLE_NORMAL[1]['translated_field_ja'])


class BasicQueryTest(NaniTestCase, OneSingleTranslatedNormalMixin):
    def test_basic(self):
        en = Normal.objects.language('en').get(pk=1)
        with self.assertNumQueries(1):
            queried = Normal.objects.language('en').get(pk=en.pk)
            self.assertEqual(queried.shared_field, en.shared_field)
            self.assertEqual(queried.translated_field, en.translated_field)
            self.assertEqual(queried.language_code, en.language_code)


class DeleteLanguageCodeTest(NaniTestCase, OneSingleTranslatedNormalMixin):
    def test_delete_language_code(self):
        en = Normal.objects.language('en').get(pk=1)
        self.assertRaises(AttributeError, delattr, en, 'language_code')

                              
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


class TableNameTest(NaniTestCase):
    def test_table_name_separator(self):
        from nani.models import TranslatedFields
        from django.db import models
        from django.conf import settings
        sep = getattr(settings, 'NANI_TABLE_NAME_SEPARATOR', '_')
        class MyModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(max_length=128)
            )
        self.assertEqual(MyModel.translations.related.model._meta.db_table, 'tests_mymodel%stranslation' % sep)

    def test_table_name_override(self):
        from nani.models import TranslatedFields
        from django.db import models
        with SettingsOverride(NANI_TABLE_NAME_SEPARATOR='O_O'):
            class MyOtherModel(TranslatableModel):
                translations = TranslatedFields(
                    hello = models.CharField(max_length=128)
                )
            self.assertEqual(MyOtherModel.translations.related.model._meta.db_table, 'tests_myothermodelO_Otranslation')

    def test_table_name_from_meta(self):
        from nani.models import TranslatedFields
        from django.db import models
        class MyNamedModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(max_length=128),
                meta = {'db_table': 'tests_mymodel_i18n'},
            )
        self.assertEqual(MyNamedModel.translations.related.model._meta.db_table, 'tests_mymodel_i18n')


class GetOrCreateTest(NaniTestCase):
    def test_create_new_translatable_instance(self):
        with self.assertNumQueries(3):
            """
            1: get
            2: create shared
            3: create translation
            """
            en, created = Normal.objects.language('en').get_or_create(
                shared_field="shared",
                defaults={'translated_field': 'English',},
            )
        self.assertTrue(created)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")

    def test_create_new_language(self):
        en = Normal.objects.language('en').create(
            shared_field="shared",
            translated_field='English',
        )
        with self.assertNumQueries(3):
            """
            1: get
            2: create shared
            3: create translation
            """
            ja, created = Normal.objects.language('ja').get_or_create(
                shared_field="shared",
                defaults={'translated_field': u'日本語',},
            )
        self.assertTrue(created)
        self.assertEqual(ja.shared_field, "shared")
        self.assertEqual(ja.translated_field, u'日本語')
        self.assertEqual(ja.language_code, "ja")
        self.assertNotEqual(en.pk, ja.pk)

    def test_get_existing_language(self):
        Normal.objects.language('en').create(
            shared_field="shared",
            translated_field='English',
        )
        with self.assertNumQueries(1):
            """
            1: get
            """
            en, created = Normal.objects.language('en').get_or_create(
                shared_field="shared",
                defaults={'translated_field': 'x-English',},
            )
        self.assertFalse(created)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")

    # Evil starts here

    def test_split_params(self):
        en, created = Normal.objects.language('en').get_or_create(
            shared_field="shared",
            translated_field="English",
        )
        self.assertTrue(created)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")

    def test_split_params_shared_already_exists(self):
        Normal.objects.language('en').create(
            shared_field="shared",
            translated_field="English",
        )
        en, created = Normal.objects.language('en').get_or_create(
            shared_field="shared",
            translated_field="x-English"
        )
        self.assertTrue(created)

    def test_new_language_split_params(self):
        en = Normal.objects.language('en').create(
            shared_field="shared",
            translated_field="English",
        )
        ja, created = Normal.objects.language('ja').get_or_create(
            shared_field="shared",
            translated_field=u'日本語',
        )
        self.assertTrue(created)
        self.assertEqual(ja.shared_field, "shared")
        self.assertEqual(ja.translated_field, u'日本語')
        self.assertEqual(ja.language_code, "ja")
        self.assertNotEqual(en.pk, ja.pk)

    def test_split_defaults(self):
        en, created = MultipleFields.objects.language('en').get_or_create(
            first_shared_field="shared-one",
            first_translated_field='English-one',
            defaults={
                'second_shared_field': 'shared-two',
                'second_translated_field': 'English-two',
            }
        )
        self.assertTrue(created)
        self.assertEqual(en.first_shared_field, "shared-one")
        self.assertEqual(en.second_shared_field, "shared-two")
        self.assertEqual(en.first_translated_field, "English-one")
        self.assertEqual(en.second_translated_field, "English-two")
        self.assertEqual(en.language_code, "en")

    def test_new_language_split_defaults(self):
        en = MultipleFields.objects.language('en').create(
            first_shared_field="shared-one",
            second_shared_field='shared-two',
            first_translated_field='English-one',
            second_translated_field='English-two',
        )
        ja, created = MultipleFields.objects.language('ja').get_or_create(
            first_shared_field="shared-one",
            first_translated_field=u'日本語-一',
            defaults={
                'second_shared_field': 'x-shared-two',
                'second_translated_field': u'日本語-二',
            }
        )
        self.assertTrue(created)
        self.assertEqual(ja.first_shared_field, "shared-one")
        #self.assertEqual(ja.second_shared_field, "shared-two")
        self.assertEqual(ja.first_translated_field, u'日本語-一')
        self.assertEqual(ja.second_translated_field,  u'日本語-二')
        self.assertEqual(ja.language_code, "ja")
        self.assertNotEqual(en.pk, ja.pk)
