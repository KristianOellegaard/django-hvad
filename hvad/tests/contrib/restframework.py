# -*- coding: utf-8 -*-
from django.utils import translation
from rest_framework.serializers import ModelSerializer, CharField
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, Related, TranslatedMany
from hvad.test_utils.data import NORMAL
from hvad.test_utils.fixtures import NormalFixture
from hvad.contrib.restframework import (TranslationsMixin,
                                        TranslatableModelSerializer)
from hvad.contrib.restframework.serializers import TranslationListSerializer

#=============================================================================

class AutoSerializer(TranslatableModelSerializer):
    class Meta:
        model = Normal
        exclude = []

class ManualSerializer(TranslatableModelSerializer):
    class Meta:
        model = Normal
        fields = ['shared_field', 'translated_field']

class ExcludeSerializer(TranslatableModelSerializer):
    class Meta:
        model = Normal
        exclude = ['translated_field']

class TranslationsSerializer(TranslationsMixin, ModelSerializer):
    class Meta:
        model = Normal
        exclude = []

class CombinedSerializer(TranslationsMixin, TranslatableModelSerializer):
    class Meta:
        model = Normal
        exclude = []

class CustomTranslationSerializer(ModelSerializer):
    # 'cheat' tests that shared fields are accessible to the translation serializer
    # It is relevant, it ensures custom serializers see the full object, along with
    # any @property. Default serializer will just get to translated fields through
    # their accessors on the shared object and work transparently.
    cheat = CharField(max_length=250, source='shared_field')
    custom = CharField(max_length=250, source='translated_field')
    class Meta:
        exclude = ('translated_field',)

class CustomSerializer(TranslationsMixin, ModelSerializer):
    class Meta:
        model = Normal
        exclude = []
        translations_serializer = CustomTranslationSerializer

class RelatedSerializer(TranslatableModelSerializer):
    class Meta:
        model = Related
        exclude = []

class RelatedTranslationsSerializer(TranslationsMixin, ModelSerializer):
    class Meta:
        model = Related
        exclude = []

#=============================================================================

class TranslatableModelSerializerTests(HvadTestCase, NormalFixture):
    'Checking the serializer representation of objects'
    normal_count = 2

    #---------------------------------------------------------------------

    def test_modelserializer_fields(self):
        'Check serializers fields are properly set'
        serializer = AutoSerializer()
        self.assertCountEqual(serializer.fields,
                              ['id', 'shared_field', 'translated_field', 'language_code'])

        serializer = ManualSerializer()
        self.assertCountEqual(serializer.fields,
                              ['shared_field', 'translated_field'])

        serializer = ExcludeSerializer()
        self.assertCountEqual(serializer.fields,
                              ['id', 'shared_field', 'language_code'])

    #---------------------------------------------------------------------

    def test_serialize_normal(self):
        'Serialize translated fields using instance language'
        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])

        serializer = AutoSerializer(instance=obj)
        data = serializer.data
        self.assertCountEqual(data, ['id', 'shared_field', 'translated_field', 'language_code'])
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(data['translated_field'], NORMAL[1].translated_field['ja'])
        self.assertEqual(data['language_code'], 'ja')

    def test_serialize_enforce_wrong(self):
        'Serialize translated fields while enforcing a language - wrong translation'
        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])

        serializer = AutoSerializer(instance=obj, language='en')
        data = serializer.data
        self.assertCountEqual(data, ['id', 'shared_field', 'translated_field', 'language_code'])
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(data['translated_field'], NORMAL[1].translated_field['en'])
        self.assertEqual(data['language_code'], 'en')

    def test_serialize_enforce_nonexistent(self):
        'Serialize translated fields while enforcing a language - nonexistent translation'
        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])

        serializer = AutoSerializer(instance=obj, language='xx')
        data = serializer.data
        self.assertCountEqual(data, ['id', 'shared_field', 'translated_field', 'language_code'])
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(data['translated_field'], '')
        self.assertEqual(data['language_code'], 'xx')

    def test_serialize_related(self):
        'Serialize relation fields'
        obj = Related(pk=42, language_code='ja',
                      normal_id=self.normal_id[1], translated_id=self.normal_id[2])

        serializer = RelatedSerializer(instance=obj)
        data = serializer.data

        self.assertCountEqual(data, ['id', 'normal', 'language_code',
                                     'translated', 'translated_to_translated'])
        self.assertEqual(data['id'], 42)
        self.assertEqual(data['normal'], self.normal_id[1])
        self.assertEqual(data['language_code'], 'ja')
        self.assertEqual(data['translated'], self.normal_id[2])
        self.assertEqual(data['translated_to_translated'], None)

    #---------------------------------------------------------------------

    def test_create_normal(self):
        'Deserialize a new instance'
        data = {
            'shared_field': 'shared',
            'translated_field': 'translated',
            'language_code': 'en'
        }
        serializer = AutoSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertIsNotNone(obj.pk)
        self.assertSavedObject(obj, 'en', **data)

    def test_create_normal_no_language(self):
        'Deserialize a new instance, without including any translated field'
        data = {
            'shared_field': 'shared',
        }
        serializer = AutoSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with translation.override('en'):
            obj = serializer.save()
        self.assertIsNotNone(obj.pk)
        self.assertSavedObject(obj, 'en', **data)
        self.assertEqual(obj.language_code, 'en')

    def test_create_enforce(self):
        'Deserialize a new instance, with language-enforcing mode'
        data = {
            'shared_field': 'shared',
            'translated_field': 'translated',
        }
        serializer = AutoSerializer(data=data, language='sr')
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertIsNotNone(obj.pk)
        self.assertSavedObject(obj, 'sr', **data)

    def test_create_enforce_violation(self):
        'Deserialize a new instance, with language-enforcing mode and language_code'
        data = {
            'shared_field': 'shared',
            'translated_field': 'translated',
            'language_code': 'en',
        }
        serializer = AutoSerializer(data=data, language='en')
        self.assertFalse(serializer.is_valid())
        serializer = AutoSerializer(data=data, language='xx')
        self.assertFalse(serializer.is_valid())

    def test_update_normal_default(self):
        'Deserialize an existing instance using instance-loaded language'
        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
        data = {
            'shared_field': 'shared',
            'translated_field': 'translated',
        }
        serializer = AutoSerializer(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        self.assertSavedObject(obj, 'ja', **data)

        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        serializer = AutoSerializer(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())
        with translation.override('en'):
            obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        self.assertSavedObject(obj, 'en', **data)

    def test_update_normal_language_code(self):
        'Deserialize an existing instance using submitted language'
        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
        data = {
            'shared_field': 'shared',
            'translated_field': 'translated',
            'language_code': 'sr'
        }
        serializer = AutoSerializer(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        self.assertSavedObject(obj, 'sr', **data)

        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        data['translated_field'] = 'translated_bis'
        serializer = AutoSerializer(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())
        with translation.override('en'):
            obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        self.assertSavedObject(obj, 'sr', **data)

    def test_update_enforce(self):
        'Deserialize an existing intance in language-enforcing mode'
        data = {
            'shared_field': 'shared',
            'translated_field': 'translated',
        }
        # Correct translation
        obj = Normal.objects.language('ja').get(pk=self.normal_id[1])
        serializer = AutoSerializer(instance=obj, data=data, language='ja')
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        self.assertSavedObject(obj, 'ja', **data)

        # Wrong translation
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        serializer = AutoSerializer(instance=obj, data=data, language='ja')
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        self.assertSavedObject(obj, 'ja', **data)

        # Nonexistent translation
        obj = Normal.objects.language('en').get(pk=self.normal_id[1])
        serializer = AutoSerializer(instance=obj, data=data, language='sr')
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        self.assertSavedObject(obj, 'sr', **data)

#=============================================================================

class TranslationsMixinTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_translations_mixin_fields(self):
        'Check serializers fields are properly set'
        serializer = TranslationsSerializer()
        self.assertCountEqual(serializer.fields,
                              ['id', 'shared_field', 'translations'])
        self.assertIsInstance(serializer.fields['translations'], TranslationListSerializer)
        self.assertCountEqual(serializer.fields['translations'].child.fields,
                              ['translated_field'])

        serializer = CustomSerializer()
        self.assertCountEqual(serializer.fields,
                              ['id', 'shared_field', 'translations'])
        self.assertIsInstance(serializer.fields['translations'], TranslationListSerializer)
        self.assertIsInstance(serializer.fields['translations'].child, CustomTranslationSerializer)
        self.assertCountEqual(serializer.fields['translations'].child.fields, ['cheat', 'custom'])

    #---------------------------------------------------------------------

    def test_serialize(self):
        'Serialize nested translations as a language => fields dict'
        obj = Normal.objects.prefetch_related('translations').get(pk=self.normal_id[1])

        serializer = TranslationsSerializer(instance=obj)
        data = serializer.data
        self.assertCountEqual(data, ['id', 'shared_field', 'translations'])
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertIsInstance(data['translations'], dict)
        self.assertCountEqual(data['translations'], self.translations)
        for language in self.translations:
            translation = data['translations'][language]
            self.assertCountEqual(translation, ['translated_field'])
            self.assertEqual(translation['translated_field'], NORMAL[1].translated_field[language])

    def test_serialize_custom(self):
        'Serialize nested translations as a language => fields dict'
        obj = Normal.objects.prefetch_related('translations').get(pk=self.normal_id[1])

        serializer = CustomSerializer(instance=obj)
        data = serializer.data
        self.assertCountEqual(data, ['id', 'shared_field', 'translations'])
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertIsInstance(data['translations'], dict)
        self.assertCountEqual(data['translations'], self.translations)
        for language in self.translations:
            translation = data['translations'][language]
            self.assertCountEqual(translation, ['cheat', 'custom'])
            self.assertEqual(translation['cheat'], NORMAL[1].shared_field)
            self.assertEqual(translation['custom'], NORMAL[1].translated_field[language])

    def test_serialize_related(self):
        'Serialize relation fields'
        obj = Related.objects.language('ja').create(
            normal_id=self.normal_id[1], translated_id=self.normal_id[2]
        )

        serializer = RelatedTranslationsSerializer(instance=obj)
        data = serializer.data

        self.assertCountEqual(data, ['id', 'normal', 'translated_fields'])
        self.assertEqual(data['id'], obj.pk)
        self.assertEqual(data['normal'], self.normal_id[1])
        self.assertIsInstance(data['translated_fields'], dict)
        for language in ['ja']:
            translation = data['translated_fields'][language]
            self.assertCountEqual(translation, ['translated', 'translated_to_translated'])
            self.assertEqual(translation['translated'], self.normal_id[2])
            self.assertEqual(translation['translated_to_translated'], None)

    #---------------------------------------------------------------------

    def test_invalid(self):
        'Submit invalid data'
        # No translations
        data = {
            'shared_field': 'shared',
            'translations': {},
        }
        serializer = TranslationsSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors['translations'])

        # Invalid translations type
        data = {
            'shared_field': 'shared',
            'translations': [
                { 'translated_field': 'English', },
            ],
        }
        serializer = TranslationsSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors['translations'])

        # Cascade invalid child
        data = {
            'shared_field': 'shared',
            'translations': {
                'en': { 'translated_field': 'x'*999 },
            },
        }
        serializer = TranslationsSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors['translations'])
        self.assertTrue(serializer.errors['translations']['en'])
        self.assertTrue(serializer.errors['translations']['en']['translated_field'])

    #---------------------------------------------------------------------

    def test_create(self):
        'Create a new Normal instance, with two translations'
        data = {
            'shared_field': 'shared',
            'translations': {
                'en': { 'translated_field': 'English', },
                'sr': { 'translated_field': u'српски', },
            },
        }
        serializer = TranslationsSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertNumQueries(3):  # insert shared, insert "en", insert "sr"
            obj = serializer.save()
        self.assertIsNot(obj.pk, None)
        qs = Normal.objects.language('all').filter(pk=obj.pk)
        self.assertCountEqual([(item.language_code, item.translated_field) for item in qs],
                              [('en', 'English'), ('sr', u'српски')])

    def test_update(self):
        'Update an existing normal instance: 1 new, 1 updated, 1 deleted translations'
        obj = Normal.objects.untranslated().prefetch_related('translations').get(pk=self.normal_id[1])
        data = {
            'shared_field': 'shared',
            'translations': {
                'en': { 'translated_field': 'English', }, # should updated
                'sr': { 'translated_field': u'српски', }, # should create
            },                                            # Japanese should be deleted
        }
        serializer = TranslationsSerializer(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertNumQueries(4):  # update shared, update "en", insert "sr", delete others
            obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        qs = Normal.objects.language('all').filter(pk=self.normal_id[1])
        self.assertCountEqual([(item.language_code, item.translated_field) for item in qs],
                              [('en', 'English'), ('sr', u'српски')])

    def test_update_partial(self):
        'Update an existing instance, but just some fields'
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        data = {
            'shared_field': 'shared'
        }
        serializer = TranslationsSerializer(instance=obj, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        with self.assertNumQueries(1):  # update shared
            obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        qs = Normal.objects.language('all').filter(pk=self.normal_id[1], shared_field='shared')
        self.assertCountEqual([item.language_code for item in qs], self.translations)

    def test_update_translated_many(self):
        'Update an existing instance, with an excluded translated M2M field'
        """ WARNING - this is unsupported, this test case is here so we know
            what we break rather than to enforce that behavior
        """
        obj = TranslatedMany.objects.language('en').create(name='shared', translated_field='English')
        # reload with normal caching conditions so query counting works
        obj = TranslatedMany.objects.untranslated().prefetch_related('translations').get(pk=obj.pk)
        data = {
            'name': 'shared-updated',
            'translations': {
                'en': {'translated_field': u'English-updated'},
                'fr': {'translated_field': u'French-added'},
            },
        }
        class TranslationSerializerClass(ModelSerializer):
            class Meta:
                exclude = ['many']
        class SerializerClass(TranslationsMixin, ModelSerializer):
            class Meta:
                model = TranslatedMany
                exclude = []
                translations_serializer = TranslationSerializerClass

        serializer = SerializerClass(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())
        with self.assertNumQueries(4):  # update shared, update en, insert fr
                                        # select to delete (none so no actual delete after)
            serializer.save()

#=============================================================================

class CombinedTests(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_combined_fields(self):
        'Check serializers fields are properly set'
        serializer = CombinedSerializer()
        self.assertCountEqual(serializer.fields,
                              ['id', 'shared_field', 'translated_field', 'language_code', 'translations'])
        self.assertIsInstance(serializer.fields['translations'], TranslationListSerializer)
        self.assertCountEqual(serializer.fields['translations'].child.fields,
                              ['translated_field'])

    #---------------------------------------------------------------------

    def test_serialize(self):
        'Serialize translations as a language => fields dict + naive fields'
        obj = Normal.objects.language('ja').prefetch_related('translations').get(pk=self.normal_id[1])

        serializer = CombinedSerializer(instance=obj)
        data = serializer.data
        self.assertCountEqual(data, ['id', 'shared_field', 'translated_field', 'language_code', 'translations'])
        self.assertEqual(data['id'], self.normal_id[1])
        self.assertEqual(data['shared_field'], NORMAL[1].shared_field)
        self.assertEqual(data['translated_field'], NORMAL[1].translated_field['ja'])
        self.assertEqual(data['language_code'], 'ja')
        self.assertIsInstance(data['translations'], dict)
        self.assertCountEqual(data['translations'], self.translations)
        for language in self.translations:
            translation = data['translations'][language]
            self.assertCountEqual(translation, ['translated_field'])
            self.assertEqual(translation['translated_field'], NORMAL[1].translated_field[language])

    #---------------------------------------------------------------------

    def test_create_translations(self):
        'Create a new Normal instance, with two translations'
        data = {
            'shared_field': 'shared',
            'translated_field': 'should be ignored',
            'language_code': 'sr',
            'translations': {
                'en': { 'translated_field': 'English', },
                'sr': { 'translated_field': u'српски', },
            },
        }
        serializer = CombinedSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertIsNot(obj.pk, None)
        qs = Normal.objects.language('all').filter(pk=obj.pk)
        self.assertCountEqual([(item.language_code, item.translated_field) for item in qs],
                              [('en', 'English'), ('sr', u'српски')])

    def test_create_translatable(self):
        'Create a new Normal instance, in translatablemodelserializer style'
        data = {
            'shared_field': 'shared',
            'translated_field': u'српски',
            'language_code': 'sr'
        }
        serializer = CombinedSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertIsNot(obj.pk, None)
        qs = Normal.objects.language('all').filter(pk=obj.pk)
        self.assertCountEqual([(item.language_code, item.translated_field) for item in qs],
                              [('sr', u'српски')])

    def test_update_translations(self):
        'Update an existing normal instance: 1 new, 1 updated, 1 deleted translations'
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        data = {
            'shared_field': 'shared',
            'language_code': 'ignored',
            'translations': {
                'en': { 'translated_field': 'English', }, # should updated
                'sr': { 'translated_field': u'српски', }, # should create
            },                                            # Japanese should be deleted
        }
        serializer = CombinedSerializer(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        qs = Normal.objects.language('all').filter(pk=self.normal_id[1])
        self.assertCountEqual([(item.language_code, item.translated_field) for item in qs],
                              [('en', 'English'), ('sr', u'српски')])

    def test_update_translatable(self):
        'Update an existing normal instance translation in translatablemodel mode'
        obj = Normal.objects.untranslated().get(pk=self.normal_id[1])
        data = {
            'shared_field': 'shared',
            'translated_field': u'српски',
            'language_code': 'sr'
        }
        serializer = CombinedSerializer(instance=obj, data=data)
        self.assertTrue(serializer.is_valid())

        obj = serializer.save()
        self.assertEqual(obj.pk, self.normal_id[1])
        qs = Normal.objects.language('all').filter(pk=self.normal_id[1])
        self.assertCountEqual([(item.language_code, item.translated_field) for item in qs],
                              [('en', NORMAL[1].translated_field['en']),
                               ('ja', NORMAL[1].translated_field['ja']),
                               ('sr', u'српски')])
