# -*- coding: utf-8 -*-
from __future__ import with_statement
import django
from django.apps import apps
from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import connection, models, IntegrityError
from django.db.models.manager import Manager
from django.db.models.query_utils import Q
from django.utils import translation
from hvad import settings
from hvad.exceptions import WrongManager
from hvad.manager import TranslationQueryset
from hvad.models import TranslatableModel, TranslatedFields
from hvad.utils import get_cached_translation
from hvad.test_utils.data import NORMAL
from hvad.test_utils.fixtures import NormalFixture
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, Unique, Related, MultipleFields, Boolean, Standard
from copy import deepcopy


class SettingsTests(HvadTestCase):
    def test_hvad_setting_namespace_error(self):
        with self.settings(HVAD_SOMETHING='foo', HVAD_OTHERTHING='bar'):
            errors = settings.check(apps)
        for key in 'HVAD_SOMETHING', 'HVAD_OTHERTHING':
            self.assertIn(checks.Critical(
                'HVAD setting in global namespace',
                hint='HVAD settings are now namespaced in the HVAD dict.',
                obj=key,
                id='hvad.settings.C01'
            ), errors)

    def test_table_name_separator(self):
        with self.settings(HVAD={'TABLE_NAME_SEPARATOR': 'foo'}):
            errors = settings.check(apps)
        self.assertIn(checks.Error('Obsolete setting HVAD["TABLE_NAME_SEPARATOR"]',
            hint='TABLE_NAME_SEPARATOR has been superceded by TABLE_NAME_FORMAT. '
                 'Set it to "%sfootranslation" to keep the old behavior',
            obj='TABLE_NAME_SEPARATOR',
            id='hvad.settings.E01',
        ), errors)

    def test_languages(self):
        with self.settings(HVAD={'LANGUAGES': [('fr', 'French'), ('en', 'English')]}):
            self.assertFalse(settings.check(apps))
            self.assertIsInstance(settings.hvad_settings.LANGUAGES, tuple)

        error = checks.Error('HVAD["LANGUAGES"] must be a sequence of (code, name)'
                             'tuples describing languages',
                             obj='LANGUAGES', id='hvad.settings.E02')
        with self.settings(HVAD={'LANGUAGES': 'fr'}):
            self.assertIn(error, settings.check(apps))
        with self.settings(HVAD={'LANGUAGES': [['fr', 'French']]}):
            self.assertIn(error, settings.check(apps))
        with self.settings(HVAD={'LANGUAGES': [('fr', 'French', 42)]}):
            self.assertIn(error, settings.check(apps))

    def test_fallback_languages(self):
        with self.settings(HVAD={'FALLBACK_LANGUAGES': ['fr']}):
            self.assertFalse(settings.check(apps))
            self.assertIsInstance(settings.hvad_settings.FALLBACK_LANGUAGES, tuple)

        error = checks.Error('HVAD["FALLBACK_LANGUAGES"] must be a sequence of language codes',
                             obj='FALLBACK_LANGUAGES', id='hvad.settings.E03')
        with self.settings(HVAD={'FALLBACK_LANGUAGES': 'fr'}):
            self.assertIn(error, settings.check(apps))
        with self.settings(HVAD={'FALLBACK_LANGUAGES': (('fr', 'French'), )}):
            self.assertIn(error, settings.check(apps))

    def test_table_name_format(self):
        error = checks.Error('HVAD["TABLE_NAME_FORMAT"] must contain exactly one string '
                             'specifier ("%s")', obj='TABLE_NAME_FORMAT', id='hvad.settings.E04')
        with self.settings(HVAD={'TABLE_NAME_FORMAT': 'foo'}):
            self.assertIn(error, settings.check(apps))
        with self.settings(HVAD={'TABLE_NAME_FORMAT': 'foo%strans%slation'}):
            self.assertIn(error, settings.check(apps))

    def test_boolean_settings(self):
        for key, err in (('AUTOLOAD_TRANSLATIONS', 'W02'), ('USE_DEFAULT_QUERYSET', 'W03')):
            error = checks.Warning('HVAD["%s"] should be True or False' % key,
                                   obj=key, id='hvad.settings.%s' % err)
            with self.settings(HVAD={key: 'foo'}):
                self.assertIn(error, settings.check(apps))

    def test_unknown_setting(self):
        error = checks.Warning('Unknown setting HVAD[\'UNKNOWN\']', obj='UNKNOWN',
                               id='hvad.settings.W01')
        with self.settings(HVAD={'UNKNOWN': 'foo'}):
            self.assertIn(error, settings.check(apps))


class DefinitionTests(HvadTestCase):
    def test_invalid_manager(self):
        class InvalidModel(TranslatableModel):
            translations = TranslatedFields(
                translated=models.CharField(max_length=250)
            )
            object = Manager()
        errors = InvalidModel.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'hvad.models.E02')
    
    def test_no_translated_fields(self):
        with self.assertRaises(ImproperlyConfigured):
            class InvalidModel2(TranslatableModel):
                pass

    def test_field_name_clash_check(self):
        class ClashingFieldsModel(TranslatableModel):
            field = models.CharField(max_length=50)
            translations = TranslatedFields(
                field=models.CharField(max_length=50)
            )
        errors = ClashingFieldsModel.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'hvad.models.E01')

    def test_ordering_invalid(self):
        class InvalidOrderingModel(TranslatableModel):
            shared_field = models.CharField(max_length=50)
            translations = TranslatedFields(
                field=models.CharField(max_length=50),
            )
            class Meta:
                ordering = 'shared_field'
        self.assertIn(checks.Error("'ordering' must be a tuple or list.", hint=None,
                                   obj=InvalidOrderingModel, id='models.E014'),
                      InvalidOrderingModel.check())

    def test_multi_table_raises(self):
        with self.assertRaises(TypeError):
            class InvalidModel3(Normal):
                translations = TranslatedFields(
                    other_translated = models.CharField(max_length=250)
                )

    def test_order_with_respect_to_raises(self):
        with self.assertRaises(ImproperlyConfigured):
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

    def test_unique_together_migration(self):
        class UniqueTogetherModel3(TranslatableModel):
            sfield_a = models.CharField(max_length=250)
            sfield_b = models.CharField(max_length=250)
            translations = TranslatedFields(
                tfield_a = models.CharField(max_length=250),
                tfield_b = models.CharField(max_length=250),
            )
            class Meta:
                unique_together = [('sfield_a', 'sfield_b'), ('tfield_a', 'tfield_b')]

        from django.db.migrations.state import ModelState
        state = ModelState.from_model(UniqueTogetherModel3)
        self.assertEqual(state.options['unique_together'], {('sfield_a', 'sfield_b')})

        state = ModelState.from_model(UniqueTogetherModel3._meta.translations_model)
        self.assertEqual(state.options['unique_together'], {('language_code', 'master'),
                                                            ('tfield_a', 'tfield_b')})

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

        with self.assertRaises(ImproperlyConfigured):
            class InvalidIndexTogetherModel(TranslatableModel):
                sfield = models.CharField(max_length=250)
                translations = TranslatedFields(
                    tfield = models.CharField(max_length=250)
                )
                class Meta:
                    index_together = [('sfield', 'tfield')]

    def test_index_together_migration(self):
        class IndexTogetherModel2(TranslatableModel):
            sfield_a = models.CharField(max_length=250)
            sfield_b = models.CharField(max_length=250)
            translations = TranslatedFields(
                tfield_a = models.CharField(max_length=250),
                tfield_b = models.CharField(max_length=250),
            )
            class Meta:
                index_together = [('sfield_a', 'sfield_b'), ('tfield_a', 'tfield_b')]

        from django.db.migrations.state import ModelState
        state = ModelState.from_model(IndexTogetherModel2)
        self.assertEqual(state.options['index_together'], {('sfield_a', 'sfield_b')})

        state = ModelState.from_model(IndexTogetherModel2._meta.translations_model)
        self.assertEqual(state.options['index_together'], {('tfield_a', 'tfield_b')})

    def test_abstract_base_model(self):
        class Meta:
            abstract = True
        attrs = {
            'Meta': Meta,
            '__module__': 'hvad.test_utils.project.app',
        }
        model = type('MyBaseModel', (TranslatableModel,), attrs)
        self.assertTrue(model._meta.abstract)

    def test_custom_base_model(self):
        class CustomTranslation(models.Model):
            def test(self):
                return 'foo'
            class Meta:
                abstract = True
        class CustomBaseModel(TranslatableModel):
            translations = TranslatedFields(
                base_class=CustomTranslation,
                tfield=models.CharField(max_length=250),
            )
        obj = CustomBaseModel(language_code='en')
        self.assertTrue(issubclass(CustomBaseModel._meta.translations_model, CustomTranslation))
        self.assertEqual(get_cached_translation(obj).test(), 'foo')

    def test_manager_properties(self):
        manager = Normal.objects
        self.assertEqual(manager.translations_model, Normal._meta.translations_model)

    def test_language_code_override(self):
        class LanguageCodeOverrideModel(TranslatableModel):
            translations = TranslatedFields(
                tfield=models.CharField(max_length=250),
                language_code=models.UUIDField(editable=False, db_index=True),
            )
        tmodel = LanguageCodeOverrideModel._meta.translations_model
        self.assertIsInstance(tmodel._meta.get_field('language_code'), models.UUIDField)


class OptionsTest(HvadTestCase):
    def test_options(self):
        self.assertEqual(Normal._meta.translations_model.__name__, 'NormalTranslation')
        self.assertEqual(Normal._meta.translations_accessor, 'translations')
        if django.VERSION < (1, 9):
            self.assertRaises(FieldDoesNotExist, Normal._meta.get_field_by_name, 'inexistent_field')
            self.assertRaises(WrongManager, Normal._meta.get_field_by_name, 'translated_field')
        self.assertRaises(FieldDoesNotExist, Normal._meta.get_field, 'inexistent_field')
        self.assertRaises(WrongManager, Normal._meta.get_field, 'translated_field')
        self.assertIs(Normal._meta.get_field(Normal._meta.translations_accessor).field.model,
                      Normal._meta.translations_model)


class QuerysetTest(HvadTestCase):
    def test_deepcopy(self):
        qs = Normal.objects.language().all()
        other = deepcopy(qs)
        self.assertEqual(other.model, qs.model)

    def test_bad_model(self):
        with self.assertRaises(TypeError):
            TranslationQueryset(Standard)

    def test_fallbacks_semantics(self):
        from hvad.settings import hvad_settings
        qs = Normal.objects.language().fallbacks()
        self.assertEqual(qs._language_fallbacks, hvad_settings.FALLBACK_LANGUAGES)
        qs = qs.fallbacks(None)
        self.assertEqual(qs._language_fallbacks, None)
        qs = qs.fallbacks('en', 'fr')
        self.assertEqual(qs._language_fallbacks, ('en', 'fr'))


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

    def test_create_lang_override(self):
        with self.assertRaises(ValueError):
            Normal.objects.language('en').create(
                language_code="en",
                shared_field="shared",
                translated_field='English',
            )


class UpdateTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_basic_update(self):
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        obj.shared_field = 'update_shared'
        obj.translated_field = 'update_translated'
        with self.assertNumQueries(2):
            obj.save()
        obj = Normal.objects.language().get(pk=self.normal_id[1])
        self.assertEqual(obj.shared_field, 'update_shared')
        self.assertEqual(obj.translated_field, 'update_translated')

    def test_force_update(self):
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        obj.shared_field = 'update_shared'
        obj.translated_field = 'update_translated'
        with self.assertNumQueries(2):
            obj.save(force_update=True)
        obj = Normal.objects.language().get(pk=self.normal_id[1])
        self.assertEqual(obj.shared_field, 'update_shared')
        self.assertEqual(obj.translated_field, 'update_translated')

    def test_update_fields_shared(self):
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        obj.shared_field = 'update_shared'
        obj.translated_field = 'update_translated'
        with self.assertNumQueries(1):
            obj.save(update_fields=['shared_field'])
        obj = Normal.objects.language().get(pk=self.normal_id[1])
        self.assertEqual(obj.shared_field, 'update_shared')
        self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])

    def test_update_fields_translated(self):
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        obj.shared_field = 'update_shared'
        obj.translated_field = 'update_translated'
        with self.assertNumQueries(1):
            obj.save(update_fields=['translated_field'])
        obj = Normal.objects.language().get(pk=self.normal_id[1])
        self.assertEqual(obj.shared_field, NORMAL[1].shared_field)
        self.assertEqual(obj.translated_field, 'update_translated')


class DeleteTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_basic_delete(self):
        with translation.override('en'):
            Normal.objects.language().filter(pk=self.normal_id[1]).delete()
            self.assertEqual(Normal.objects.untranslated().count(), self.normal_count - 1)
            self.assertEqual(Normal.objects.language().count(), self.normal_count - 1)
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

    def test_args_override(self):
        with self.assertRaises(Normal.DoesNotExist):
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


class DescriptorTests(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_translated_attribute_get(self):
        """ Translated attribute get behaviors """

        # Get translated attribute on class itself
        DEFAULT = 'world'
        class MyDescriptorTestModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(default=DEFAULT, max_length=128)
            )
        self.assertEqual(MyDescriptorTestModel.hello, DEFAULT)

        # Get translated attribute with a translation loaded
        obj = Normal.objects.language("en").get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])

        # Get translated attribute without a translation loaded, AUTOLOAD is false
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': False}):
                self.assertRaises(AttributeError, getattr, obj, 'translated_field')

        # Get translated attribute without a translation loaded, AUTOLOAD is true and one exists
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': True}), translation.override('ja'):
                self.assertEqual(obj.translated_field, NORMAL[1].translated_field['ja'])

        # Get translated attribute without a translation loaded, AUTOLOAD is true but none exists
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': True}), translation.override('fr'):
                self.assertRaises(AttributeError, getattr, obj, 'translated_field')

    def test_translated_attribute_set(self):
        """ Translated attribute set behaviors """

        # Set translated attribute with a translation loaded
        obj = Normal.objects.language("en").get(pk=self.normal_id[1])
        trans = get_cached_translation(obj)
        with self.assertNumQueries(0):
            obj.translated_field = 'foo'
            self.assertNotIn('translated_field', obj.__dict__)
            self.assertEqual(trans.__dict__['translated_field'], 'foo')

        # Set translated attribute without a translation loaded, AUTOLOAD is false
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': False}):
                self.assertRaises(AttributeError, setattr, obj, 'translated_field', 'foo')

        # Set translated attribute without a translation loaded, AUTOLOAD is true and one exists
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': True}), translation.override('ja'):
                obj.translated_field = 'foo'
                trans = get_cached_translation(obj)
                self.assertNotIn('translated_field', obj.__dict__)
                self.assertEqual(trans.__dict__['translated_field'], 'foo')

        # Set translated attribute without a translation loaded, AUTOLOAD is true but none exists
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': True}), translation.override('fr'):
                self.assertRaises(AttributeError, setattr, obj, 'translated_field', 'foo')

    def test_translated_attribute_delete(self):    
        """ Translated attribute delete behaviors """

        # Delete a translated field with a translation loaded
        obj = Normal.objects.language("en").get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            del obj.translated_field
        if django.VERSION >= (1, 10):   # on version 1.10 and newer, this refreshes from db
            with self.assertNumQueries(1):
                self.assertEqual(obj.translated_field, NORMAL[1].translated_field['en'])
        else:
            with self.assertNumQueries(0):
                self.assertRaises(AttributeError, getattr, obj, 'translated_field')

        # Delete a translated field without a translation loaded, AUTOLOAD is false
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(0):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': False}):
                self.assertRaises(AttributeError, delattr, obj, 'translated_field')

        # Delete translated attribute without a translation loaded, AUTOLOAD is true and one exists
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            with translation.override('en'):
                del obj.translated_field

        # Delete translated attribute without a translation loaded, AUTOLOAD is true but none exists
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            with self.settings(HVAD={'AUTOLOAD_TRANSLATIONS': True}), translation.override('fr'):
                self.assertRaises(AttributeError, delattr, obj, 'translated_field')

    def test_translated_foreignkey_set(self):
        """ Special behavior for ForeignKey and its remote id """
        cache = Related._meta.translations_cache

        normal = Normal.objects.language('en').get(pk=self.normal_id[1])
        related = Related(language_code='en')
        related.translated = normal
        self.assertNotIn('translated_id', related.__dict__)
        self.assertIn('translated_id', getattr(related, cache).__dict__)
        self.assertEqual(getattr(related, cache).__dict__['translated_id'], self.normal_id[1])

        related.translated_id = 4242
        self.assertNotIn('translated_id', related.__dict__)
        self.assertIn('translated_id', getattr(related, cache).__dict__)
        self.assertEqual(getattr(related, cache).__dict__['translated_id'], 4242)

    def test_language_code_attribute(self):
        """ Language code special attribute behaviors """

        obj = Normal.objects.language("en").get(pk=self.normal_id[1])

        # Get language_code with a translation loaded
        with translation.override('ja'):    # this must be ignored
            self.assertEqual(obj.language_code, 'en')

        # Get language_code without a translation loaded
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        with self.assertNumQueries(1):
            with translation.override('ja'):
                self.assertEqual(obj.language_code, 'ja')

        # Alter or delete language_code
        self.assertRaises(AttributeError, setattr, obj, 'language_code', "en")
        self.assertRaises(AttributeError, delattr, obj, 'language_code')


class TableNameTest(HvadTestCase):
    def test_table_name_separator(self):
        from hvad.models import TranslatedFields
        from django.db import models
        from hvad.settings import hvad_settings
        name_format = hvad_settings.TABLE_NAME_FORMAT
        class MyTableNameTestModel(TranslatableModel):
            translations = TranslatedFields(
                hello = models.CharField(max_length=128)
            )
        tmodel = MyTableNameTestModel._meta.translations_model
        self.assertTrue(tmodel._meta.db_table.endswith(name_format % ('_mytablenametestmodel', )))

    def test_table_name_override(self):
        from hvad.models import TranslatedFields
        from django.db import models
        with self.settings(HVAD={'TABLE_NAME_FORMAT': '%sO_Otranslation'}):
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
            2a: savepoint
            2b: create shared
            3a: create translation
            3b: release savepoint
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
            2a: savepoint
            2b: create shared
            3a: create translation
            3b: release savepoint
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

    def test_get_or_create_lang_override(self):
        with self.assertRaises(ValueError):
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
