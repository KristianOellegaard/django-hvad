# -*- coding: utf-8 -*-
from __future__ import with_statement
import django
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, models, IntegrityError
from django.db.models.manager import Manager
from django.db.models.query_utils import Q
from django.utils import translation
from hvad.compat import with_metaclass
from hvad.manager import TranslationQueryset, TranslationManager
from hvad.models import TranslatableModel, TranslatedFields
from hvad.test_utils.data import NORMAL
from hvad.test_utils.fixtures import NormalFixture
from hvad.test_utils.testcase import HvadTestCase, minimumDjangoVersion
from hvad.test_utils.project.app.models import Normal, Unique, Related, MultipleFields, Boolean, Standard
from hvad.test_utils.project.alternate_models_app.models import NormalAlternate
from copy import deepcopy


class DefinitionTests(HvadTestCase):
    def test_invalid_manager(self):
        attrs = {
            'objects': Manager(),
            '__module__': 'hvad.test_utils.project.app',
        }
        self.assertRaises(ImproperlyConfigured, type,
                          'InvalidModel', (TranslatableModel,), attrs)
    
    def test_no_translated_fields(self):
        class InvalidModel2(object):
            objects = TranslationManager()

        attrs = dict(InvalidModel2.__dict__)
        del attrs['__dict__']
        del attrs['__weakref__']
        bases = (TranslatableModel,InvalidModel2,)
        self.assertRaises(ImproperlyConfigured, type,
                          'InvalidModel2', bases, attrs)

    @minimumDjangoVersion(1, 7)
    def test_field_name_clash_check(self):
        class ClashingFieldsModel(TranslatableModel):
            field = models.CharField(max_length=50)
            translations = TranslatedFields(
                field=models.CharField(max_length=50)
            )
        errors = ClashingFieldsModel.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'hvad.models.E01')

    def test_multi_table_raises(self):
        with self.assertRaises(TypeError):
            class InvalidModel3(Normal):
                translations = TranslatedFields(
                    other_translated = models.CharField(max_length=250)
                )

    def test_order_with_respect_to_raises(self):
        with self.assertRaises(ValueError):
            class InvalidModel4(TranslatableModel):
                translations = TranslatedFields(
                    translated_field = models.CharField(max_length=250)
                )
                class Meta:
                    order_with_respect_to = 'translated_field'

    def test_unique_together(self):
        class UniqueTogetherModel(TranslatableModel):
            sfield_a = models.CharField(max_length=250)
            sfield_b = models.CharField(max_length=250)
            translations = TranslatedFields(
                tfield_a = models.CharField(max_length=250),
                tfield_b = models.CharField(max_length=250),
            )
            class Meta:
                unique_together = [('sfield_a', 'sfield_b'), ('tfield_a', 'tfield_b')]

        if django.VERSION >= (1, 7):
            errors = UniqueTogetherModel.check()
            self.assertFalse(errors)

        self.assertIn(('sfield_a', 'sfield_b'),
                         UniqueTogetherModel._meta.unique_together)
        self.assertNotIn(('tfield_a', 'tfield_b'),
                         UniqueTogetherModel._meta.unique_together)
        self.assertNotIn(('sfield_a', 'sfield_b'),
                      UniqueTogetherModel._meta.translations_model._meta.unique_together)
        self.assertIn(('tfield_a', 'tfield_b'),
                      UniqueTogetherModel._meta.translations_model._meta.unique_together)

        with self.assertThrowsWarning(DeprecationWarning):
            class DeprecatedUniqueTogetherModel(TranslatableModel):
                translations = TranslatedFields(
                    tfield_a = models.CharField(max_length=250),
                    tfield_b = models.CharField(max_length=250),
                    meta = { 'unique_together': [('tfield_a', 'tfield_b')] }
                )
        self.assertIn(('tfield_a', 'tfield_b'),
                      DeprecatedUniqueTogetherModel._meta.translations_model._meta.unique_together)

    def test_unique_together_invalid(self):
        with self.assertRaises(ImproperlyConfigured):
            class InvalidUniqueTogetherModel(TranslatableModel):
                sfield = models.CharField(max_length=250)
                translations = TranslatedFields(
                    tfield = models.CharField(max_length=250)
                )
                class Meta:
                    unique_together = [('sfield', 'tfield')]

    def test_unique_together_language_code(self):
        class UniqueTogetherModel2(TranslatableModel):
            sfield = models.CharField(max_length=250)
            translations = TranslatedFields(
                tfield_a = models.CharField(max_length=250),
                tfield_b = models.CharField(max_length=250),
            )
            class Meta:
                unique_together = [('tfield_a', 'tfield_b', 'language_code')]
        self.assertIn(('tfield_a', 'tfield_b', 'language_code'),
                      UniqueTogetherModel2._meta.translations_model._meta.unique_together)

    @minimumDjangoVersion(1, 5)
    def test_index_together(self):
        class IndexTogetherModel(TranslatableModel):
            sfield_a = models.CharField(max_length=250)
            sfield_b = models.CharField(max_length=250)
            translations = TranslatedFields(
                tfield_a = models.CharField(max_length=250),
                tfield_b = models.CharField(max_length=250),
            )
            class Meta:
                index_together = [('sfield_a', 'sfield_b'), ('tfield_a', 'tfield_b')]

        if django.VERSION >= (1, 7):
            errors = IndexTogetherModel.check()
            self.assertFalse(errors)

        self.assertIn(('sfield_a', 'sfield_b'),
                         IndexTogetherModel._meta.index_together)
        self.assertNotIn(('tfield_a', 'tfield_b'),
                         IndexTogetherModel._meta.index_together)
        self.assertNotIn(('sfield_a', 'sfield_b'),
                      IndexTogetherModel._meta.translations_model._meta.index_together)
        self.assertIn(('tfield_a', 'tfield_b'),
                      IndexTogetherModel._meta.translations_model._meta.index_together)

        with self.assertThrowsWarning(DeprecationWarning):
            class DeprecatedIndexTogetherModel(TranslatableModel):
                translations = TranslatedFields(
                    tfield_a = models.CharField(max_length=250),
                    tfield_b = models.CharField(max_length=250),
                    meta = { 'index_together': [('tfield_a', 'tfield_b')] }
                )
        self.assertIn(('tfield_a', 'tfield_b'),
                      DeprecatedIndexTogetherModel._meta.translations_model._meta.index_together)

        with self.assertRaises(ImproperlyConfigured):
            class InvalidIndexTogetherModel(TranslatableModel):
                sfield = models.CharField(max_length=250)
                translations = TranslatedFields(
                    tfield = models.CharField(max_length=250)
                )
                class Meta:
                    index_together = [('sfield', 'tfield')]

    def test_abstract_base_model(self):
        class Meta:
            abstract = True
        attrs = {
            'Meta': Meta,
            '__module__': 'hvad.test_utils.project.app',
        }
        model = type('MyBaseModel', (TranslatableModel,), attrs)
        self.assertTrue(model._meta.abstract)

    def test_internal_properties(self):
        self.assertCountEqual(Normal()._translated_field_names,
                              ['id', 'master', 'master_id', 'language_code', 'translated_field'])

    def test_manager_properties(self):
        manager = Normal.objects
        self.assertEqual(manager.translations_model, Normal._meta.translations_model)

class OptionsTest(HvadTestCase):
    def test_options(self):
        opts = Normal._meta
        self.assertTrue(hasattr(opts, 'translations_model'))
        self.assertTrue(hasattr(opts, 'translations_accessor'))
        if django.VERSION >= (1, 8):
            relmodel = Normal._meta.get_field(opts.translations_accessor).field.model
        else:
            relmodel = Normal._meta.get_field_by_name(opts.translations_accessor)[0].model
        self.assertEqual(relmodel, opts.translations_model)


class QuerysetTest(HvadTestCase):
    def test_deepcopy(self):
        qs = Normal.objects.language().all()
        other = deepcopy(qs)
        self.assertEquals(other.model, qs.model)

    def test_bad_model(self):
        with self.assertRaises(TypeError):
            TranslationQueryset(Standard)

    @minimumDjangoVersion(1, 6)
    def test_fallbacks_semantics(self):
        from hvad.manager import FALLBACK_LANGUAGES
        qs = Normal.objects.language().fallbacks()
        self.assertEquals(qs._language_fallbacks, FALLBACK_LANGUAGES)
        qs = qs.fallbacks(None)
        self.assertEquals(qs._language_fallbacks, None)
        qs = qs.fallbacks('en', 'fr')
        self.assertEquals(qs._language_fallbacks, ('en', 'fr'))

class AlternateCreateTest(HvadTestCase):
    def test_create_instance_simple(self):
        obj = NormalAlternate(language_code='en')
        obj.shared_field = "shared"
        obj.translated_field = "English"
        obj.save()
        en = NormalAlternate.objects.language('en').get(pk=obj.pk)
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")
    

class CreateTest(HvadTestCase):
    def test_create(self):
        with self.assertNumQueries(2):
            en = Normal.objects.language('en').create(
                shared_field="shared",
                translated_field='English',
            )
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")

    def test_create_nolang(self):
        with self.assertNumQueries(2):
            with translation.override('en'):
                en = Normal.objects.create(
                    shared_field="shared",
                    translated_field='English',
                )
        self.assertEqual(en.shared_field, "shared")
        self.assertEqual(en.translated_field, "English")
        self.assertEqual(en.language_code, "en")

    def test_create_invalid_lang(self):
        self.assertRaises(ValueError, Normal.objects.language().create, language_code='all')

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
        with translation.override('en'):
            obj = Normal(language_code='en')
            obj.shared_field = "shared"
            obj.translated_field = "English"
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.shared_field, "shared")
            self.assertEqual(en.translated_field, "English")
            self.assertEqual(en.language_code, "en")
        
    def test_create_instance_shared_nolang(self):
        with translation.override('en'):
            obj = Normal(language_code='en', shared_field = "shared")
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.shared_field, "shared")
            self.assertEqual(en.language_code, "en")
        
    def test_create_instance_translated_nolang(self):
        with translation.override('en'):
            obj = Normal(language_code='en', translated_field = "English")
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.translated_field, "English")
            self.assertEqual(en.language_code, "en")
    
    def test_create_instance_both_nolang(self):
        with translation.override('en'):
            obj = Normal(language_code='en', shared_field = "shared",
                         translated_field = "English")
            obj.save()
            en = Normal.objects.language('en').get(pk=obj.pk)
            self.assertEqual(en.shared_field, "shared")
            self.assertEqual(en.translated_field, "English")
            self.assertEqual(en.language_code, "en")

    def test_create_instance_untranslated(self):
        with self.assertNumQueries(1):
            with translation.override('en'):
                ut = Normal.objects.create(
                    shared_field="shared",
                )
        self.assertEqual(ut.shared_field, "shared")
        with self.assertNumQueries(1):
            with self.assertRaises(AttributeError):
                ut.translated_field
        with self.assertNumQueries(1):
            with self.assertRaises(AttributeError):
                ut.language_code

    def test_create_lang_deprecation(self):
        with self.assertRaises(RuntimeError):
            Normal.objects.language('en').create(
                language_code="en",
                shared_field="shared",
                translated_field='English',
            )


class DeleteTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_basic_delete(self):
        with translation.override('en'):
            Normal.objects.language().filter(pk=self.normal_id[1]).delete()
            self.assertEquals(Normal.objects.untranslated().count(), self.normal_count - 1)
            self.assertEquals(Normal.objects.language().count(), self.normal_count - 1)
            self.assertNotIn(self.normal_id[1],
                            [obj.pk for obj in Normal.objects.untranslated().all()])
            self.assertFalse(
                Normal._meta.translations_model.objects.filter(master_id=self.normal_id[1]).exists()
            )

    def test_multi_delete(self):
        with translation.override('en'):
            Normal.objects.language().delete()
            self.assertFalse(Normal.objects.untranslated().exists())
            self.assertFalse(Normal.objects.language().exists())
            self.assertFalse(Normal._meta.translations_model.objects.exists())


class TranslatedTest(HvadTestCase, NormalFixture):
    normal_count = 1
    translations = ('en',)

    def test_translate(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        self.assertEqual(Normal._meta.translations_model.objects.count(), 1)
        self.assertEqual(en.shared_field, NORMAL[1].shared_field)
        self.assertEqual(en.translated_field, NORMAL[1].translated_field['en'])
        ja = en
        ja.translate('ja')
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        self.assertEqual(ja.shared_field, NORMAL[1].shared_field)
        self.assertEqual(ja.translated_field, '')
        ja.translated_field = NORMAL[1].translated_field['ja']
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        self.assertEqual(ja.shared_field, NORMAL[1].shared_field)
        self.assertEqual(ja.translated_field, NORMAL[1].translated_field['ja'])

        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])

        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
        self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])


class GetTest(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_get(self):
        with self.assertNumQueries(1):
            got = Normal.objects.language('en').get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            self.assertEqual(got.shared_field, NORMAL[1].shared_field)
            self.assertEqual(got.translated_field, NORMAL[1].translated_field['en'])
            self.assertEqual(got.language_code, "en")

    def test_filtered_get(self):
        qs = Normal.objects.language('en') | Normal.objects.language('de')
        found = qs.filter(shared_field=NORMAL[1].shared_field).get(pk=self.normal_id[1])
        self.assertEqual(found.pk, self.normal_id[1])

    def test_safe_translation_getter(self):
        untranslated = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with translation.override('en'):
            self.assertEqual(untranslated.safe_translation_getter('translated_field', None), None)
            Normal.objects.untranslated().get(pk=self.normal_id[1])
            self.assertEqual(untranslated.safe_translation_getter('translated_field', "English"), "English")
        with translation.override('ja'):
            self.assertEqual(untranslated.safe_translation_getter('translated_field', None), None)
            self.assertEqual(untranslated.safe_translation_getter('translated_field', "Test"), "Test")


class GetByLanguageTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_args(self):
        with translation.override('en'):
            q = Q(language_code='ja', pk=self.normal_id[1])
            obj = Normal.objects.language('all').get(q)
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])

    def test_kwargs(self):
        with translation.override('en'):
            kwargs = {'language_code':'ja', 'pk':self.normal_id[1]}
            obj = Normal.objects.language('all').get(**kwargs)
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])

    def test_language(self):
        with translation.override('en'):
            obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
            self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])

    def test_args_override_deprecation(self):
        with self.assertRaises(RuntimeError):
            Normal.objects.language('en').get(language_code='ja', pk=self.normal_id[1])


class GetAllLanguagesTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_args(self):
        with translation.override('en'):
            q = Q(pk=self.normal_id[1])
            with self.assertNumQueries(1):
                objs = Normal.objects.language('all').filter(q)
                self.assertEqual(len(objs), 2)
                self.assertCountEqual((self.normal_id[1], self.normal_id[1]),
                                      (objs[0].pk, objs[1].pk))
                self.assertCountEqual(('en', 'ja'),
                                      (objs[0].language_code, objs[1].language_code))

    def test_kwargs(self):
        with translation.override('en'):
            kwargs = {'pk': self.normal_id[1]}
            with self.assertNumQueries(1):
                objs = Normal.objects.language('all').filter(**kwargs)
                self.assertEqual(len(objs), 2)
                self.assertCountEqual((self.normal_id[1], self.normal_id[1]),
                                      (objs[0].pk, objs[1].pk))
                self.assertCountEqual(('en', 'ja'),
                                      (objs[0].language_code, objs[1].language_code))

    def test_translated_unique(self):
        with translation.override('en'):
            with self.assertNumQueries(1):
                obj = Normal.objects.language('all').get(
                    translated_field=NORMAL[1].translated_field['ja']
                )
                self.assertEqual(obj.pk, self.normal_id[1])
                self.assertEqual(obj.language_code, 'ja')
                self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
                self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])

    def test_get_all_raises(self):
        with self.assertRaises(ValueError):
            Normal.objects.language('en').get(pk=self.normal_id[1], language_code='all')


class BasicQueryTest(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_basic(self):
        with self.assertNumQueries(1):
            queried = Normal.objects.language('en').get(pk=self.normal_id[1])
            self.assertEqual(queried.shared_field, NORMAL[1].shared_field)
            self.assertEqual(queried.translated_field, NORMAL[1].translated_field['en'])
            self.assertEqual(queried.language_code, 'en')


class DeleteLanguageCodeTest(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_delete_language_code(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        self.assertRaises(AttributeError, delattr, en, 'language_code')


class DescriptorTests(HvadTestCase):
    def test_translated_attribute_get(self):
        # 'MyDescriptorTestModel' should return the default field value,
        # in case there is no translation
        from hvad.models import TranslatedFields
        from django.db import models

        DEFAULT = 'world'
        class MyDescriptorTestModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(default=DEFAULT, max_length=128)
            )
        self.assertEqual(MyDescriptorTestModel.hello, DEFAULT)

    def test_translated_foreignkey_set(self):
        cache = Related._meta.translations_cache

        normal = Normal(language_code='en')
        normal.save()
        related = Related(language_code='en')
        related.translated = normal
        self.assertNotIn('translated_id', related.__dict__)
        self.assertIn('translated_id', getattr(related, cache).__dict__)
        self.assertEqual(getattr(related, cache).__dict__['translated_id'], normal.pk)

        related.translated_id = 4242
        self.assertNotIn('translated_id', related.__dict__)
        self.assertIn('translated_id', getattr(related, cache).__dict__)
        self.assertEqual(getattr(related, cache).__dict__['translated_id'], 4242)

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


class TableNameTest(HvadTestCase):
    def test_table_name_separator(self):
        from hvad.models import TranslatedFields
        from django.db import models
        from django.conf import settings
        sep = getattr(settings, 'HVAD_TABLE_NAME_SEPARATOR', '_')
        class MyTableNameTestModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(max_length=128)
            )
        self.assertTrue(MyTableNameTestModel._meta.translations_model._meta.db_table.endswith('_mytablenametestmodel%stranslation' % sep))

    def test_table_name_override(self):
        from hvad.models import TranslatedFields
        from django.db import models
        with self.settings(HVAD_TABLE_NAME_SEPARATOR='O_O'):
            class MyOtherTableNameTestModel(TranslatableModel):
                translations = TranslatedFields(
                    hello = models.CharField(max_length=128)
                )
            self.assertTrue(MyOtherTableNameTestModel._meta.translations_model._meta.db_table.endswith('_myothertablenametestmodelO_Otranslation'))

    def test_table_name_from_meta(self):
        from hvad.models import TranslatedFields
        from django.db import models
        class MyTableNameTestNamedModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(max_length=128),
                meta = {'db_table': 'tests_mymodel_i18n'},
            )
        self.assertEqual(MyTableNameTestNamedModel._meta.translations_model._meta.db_table, 'tests_mymodel_i18n')


class GetOrCreateTest(HvadTestCase):
    def test_create_new_translatable_instance(self):
        with self.assertNumQueries(5 if connection.features.uses_savepoints else 3):
            """
            1: get
            2a: savepoint (django >= 1.6)
            2b: create shared
            3a: create translation
            3b: release savepoint (django >= 1.6)
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
        with self.assertNumQueries(5 if connection.features.uses_savepoints else 3):
            """
            1: get
            2a: savepoint (django >= 1.6)
            2b: create shared
            3a: create translation
            3b: release savepoint (django >= 1.6)
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

    def test_get_or_create_integrity_exception(self):
        Unique.objects.language('en').create(
            shared_field='duplicated',
            translated_field='English',
            unique_by_lang='English'
        )
        with self.assertRaises(IntegrityError):
            Unique.objects.language('en').get_or_create(
                translated_field='inexistent',
                unique_by_lang='inexistent',
                defaults={'shared_field': 'duplicated'}
            )

    def test_get_or_create_invalid_lang(self):
        self.assertRaises(ValueError, Normal.objects.language().get_or_create,
                          shared_field='nonexistent', defaults={'language_code': 'all'})

    def test_get_or_create_lang_deprecation(self):
        with self.assertRaises(RuntimeError):
            Normal.objects.language('en').get_or_create(
                shared_field="shared",
                translated_field='English',
                defaults={
                    'language_code': 'en',
                }
            )


class BooleanTests(HvadTestCase):
    def test_boolean_on_shared(self):
        Boolean.objects.language('en').create(shared_flag=True, translated_flag=False)
        en = Boolean.objects.language('en').get()
        self.assertEqual(en.shared_flag, True)
        self.assertEqual(en.translated_flag, False)
