# -*- coding: utf-8 -*-
import django
from django.core.exceptions import FieldError
from django.db import connection, models, IntegrityError
from django.db.models.query_utils import Q
from hvad.exceptions import WrongManager
from hvad.models import (TranslatedFields, TranslatableModel)
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.data import NORMAL, STANDARD
from hvad.test_utils.fixtures import NormalFixture, StandardFixture
from hvad.test_utils.testcase import HvadTestCase
from hvad.utils import get_translation_aware_manager
from hvad.test_utils.project.app.models import (Normal, Related, SimpleRelated,
                                                RelatedRelated, Standard, StandardRelated)


class NormalToNormalFKTest(HvadTestCase, NormalFixture):
    normal_count = 1

    def test_relation(self):
        """
        'normal' (aka 'shared') relations are relations from the shared (or
        normal) model to another shared (or normal) model.

        They should behave like normal foreign keys in Django
        """
        normal = Normal.objects.language('en').get(pk=self.normal_id[1])
        related = Related.objects.create(normal=normal)
        self.assertEqual(related.normal.pk, normal.pk)
        self.assertEqual(related.normal.shared_field, normal.shared_field)
        self.assertEqual(related.normal.translated_field, normal.translated_field)
        self.assertTrue(related in normal.rel1.all())
    
    def test_failed_relation(self):
        related = Related.objects.create()
        related.normal_id = 999
        if connection.features.supports_forward_references:
            related.save()
            self.assertRaises(Normal.DoesNotExist, getattr, related, 'normal')
        else:
            self.assertRaises(IntegrityError, related.save)

    def test_reverse_relation(self):
        normal = Normal.objects.language('en').get(pk=self.normal_id[1])
        related = Related.objects.language('en').create(normal=normal)

        self.assertEqual(normal.rel1.language('en').get().pk, related.pk)


class StandardToTransFKTest(HvadTestCase, StandardFixture, NormalFixture):
    normal_count = 2
    standard_count = 1

    def test_relation(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        ja = Normal.objects.language('ja').get(pk=self.normal_id[1])
        related = Standard.objects.get(pk=self.standard_id[1])
        with LanguageOverride('en'):
            related = self.reload(related)
            self.assertEqual(related.normal.pk, en.pk)
            self.assertEqual(related.normal.shared_field, en.shared_field)
            self.assertEqual(related.normal.translated_field, en.translated_field)
            self.assertTrue(related in en.standards.all())
        with LanguageOverride('ja'):
            related = self.reload(related)
            self.assertEqual(related.normal.pk, ja.pk)
            self.assertEqual(related.normal.shared_field, ja.shared_field)
            self.assertEqual(related.normal.translated_field, ja.translated_field)
            self.assertTrue(related in ja.standards.all())

    def test_num_queries(self):
        with LanguageOverride('en'):
            en = Normal.objects.language('en').get(pk=self.normal_id[1])
            with self.assertNumQueries(1):
                related = Standard.objects.select_related('normal').get(pk=self.standard_id[1])
                self.assertEqual(related.normal.pk, en.pk)
            with self.assertNumQueries(0):
                self.assertEqual(related.normal.shared_field, en.shared_field)
            with self.assertNumQueries(1):
                self.assertEqual(related.normal.translated_field, en.translated_field)

    def test_lookup_by_pk(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        by_pk = Standard.objects.get(normal__pk=en.pk)
        with LanguageOverride('en'):
            self.assertEqual(by_pk.normal.pk, en.pk)
            self.assertEqual(by_pk.normal.shared_field, en.shared_field)
            self.assertEqual(by_pk.normal.translated_field, en.translated_field)
            self.assertTrue(by_pk in en.standards.all())

    def test_lookup_by_shared_field(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        by_shared_field = Standard.objects.get(normal__shared_field=en.shared_field)
        with LanguageOverride('en'):
            self.assertEqual(by_shared_field.normal.pk, en.pk)
            self.assertEqual(by_shared_field.normal.shared_field, en.shared_field)
            self.assertEqual(by_shared_field.normal.translated_field, en.translated_field)
            self.assertTrue(by_shared_field in en.standards.all())

    def test_lookup_by_translated_field(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            by_translated_field = translation_aware_manager.get(
                normal__translated_field=en.translated_field
            )
            self.assertEqual(by_translated_field.normal.pk, en.pk)
            self.assertEqual(by_translated_field.normal.shared_field, en.shared_field)
            self.assertEqual(by_translated_field.normal.translated_field, en.translated_field)
            self.assertTrue(by_translated_field in en.standards.all())

    def test_lookup_by_translated_field_requires_translation_aware_manager(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        with LanguageOverride('en'):
            self.assertRaises(WrongManager, Standard.objects.get,
                              normal__translated_field=en.translated_field)

    def test_lookup_by_non_existing_field(self):
        with LanguageOverride('en'):
            if django.VERSION >= (1, 7):
                self.assertRaises(TypeError, Standard.objects.get,
                                  normal__non_existing_field=1)
            else:
                self.assertRaises(FieldError, Standard.objects.get,
                                  normal__non_existing_field=1)

    def test_lookup_by_translated_field_using_q_objects(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            q = Q(normal__translated_field=en.translated_field)
            by_translated_field = translation_aware_manager.get(q)
            self.assertEqual(by_translated_field.normal.pk, en.pk)
            self.assertEqual(by_translated_field.normal.shared_field, en.shared_field)
            self.assertEqual(by_translated_field.normal.translated_field, en.translated_field)
            self.assertTrue(by_translated_field in en.standards.all())

    def test_filter_by_shared_field(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        with LanguageOverride('en'):
            by_shared_field = Standard.objects.filter(normal__shared_field=en.shared_field)
            normals = [obj.normal.pk for obj in by_shared_field]
            expected = [en.pk]
            self.assertEqual(normals, expected)
            shared_fields = [obj.normal.shared_field for obj in by_shared_field]
            expected_fields = [en.shared_field]
            self.assertEqual(shared_fields, expected_fields)
            translated_fields = [obj.normal.translated_field for obj in by_shared_field]
            expected_fields = [en.translated_field]
            self.assertEqual(translated_fields, expected_fields)
            for obj in by_shared_field:
                self.assertTrue(obj in en.standards.all())

    def test_filter_by_translated_field(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            by_translated_field = translation_aware_manager.filter(
                normal__translated_field=en.translated_field
            )
            normals = [obj.normal.pk for obj in by_translated_field]
            expected = [en.pk]
            self.assertEqual(normals, expected)
            shared_fields = [obj.normal.shared_field for obj in by_translated_field]
            expected_fields = [en.shared_field]
            self.assertEqual(shared_fields, expected_fields)
            translated_fields = [obj.normal.translated_field for obj in by_translated_field]
            expected_fields = [en.translated_field]
            self.assertEqual(translated_fields, expected_fields)
            for obj in by_translated_field:
                self.assertTrue(obj in en.standards.all())

    def test_filter_by_translated_field_requires_translation_aware_manager(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        with LanguageOverride('en'):
            self.assertRaises(WrongManager, Standard.objects.filter,
                              normal__translated_field=en.translated_field)

    def test_filter_by_translated_field_using_q_objects(self):
        en = Normal.objects.language('en').get(pk=self.normal_id[1])
        translation_aware_manager = get_translation_aware_manager(Standard)
        with LanguageOverride('en'):
            q = Q(normal__translated_field=en.translated_field)
            by_translated_field = translation_aware_manager.filter(q)
            normals = [obj.normal.pk for obj in by_translated_field]
            expected = [en.pk]
            self.assertEqual(normals, expected)
            shared_fields = [obj.normal.shared_field for obj in by_translated_field]
            expected_fields = [en.shared_field]
            self.assertEqual(shared_fields, expected_fields)
            translated_fields = [obj.normal.translated_field for obj in by_translated_field]
            expected_fields = [en.translated_field]
            self.assertEqual(translated_fields, expected_fields)
            for obj in by_translated_field:
                self.assertTrue(obj in en.standards.all())


class TripleRelationTests(HvadTestCase, StandardFixture, NormalFixture):
    normal_count = 1
    standard_count = 1

    def test_triple(self):
        normal = Normal.objects.language('en').get(pk=self.normal_id[1])
        standard = Standard.objects.get(pk=self.standard_id[1])
        simple = SimpleRelated.objects.language('en').create(normal=normal)

        obj = Normal.objects.language('en').get(standards__pk=standard.pk)
        self.assertEqual(obj.pk, normal.pk)

        obj = Normal.objects.language('en').get(simplerel__pk=simple.pk)
        self.assertEqual(obj.pk, normal.pk)

        # We created an english Normal object, so we want to make sure that we use 'en'
        with LanguageOverride('en'):
            obj = get_translation_aware_manager(Standard).get(normal__simplerel__pk=simple.pk)
            self.assertEqual(obj.pk, standard.pk)

        # If we don't use language 'en', it should give DoesNotExist, when using the
        # translation aware manager
        with LanguageOverride('ja'):
            manager = get_translation_aware_manager(Standard)
            self.assertRaises(Standard.DoesNotExist, manager.get, normal__simplerel__pk=simple.pk)

        # However, if we don't use the translation aware manager, we can query any
        # the shared fields in any language, and it should return the object,
        # even though there is no translated Normal objects
        with LanguageOverride('ja'):
            obj = Standard.objects.get(normal__simplerel__pk=simple.pk)
            self.assertEqual(obj.pk, standard.pk)


class ManyToManyTest(HvadTestCase, NormalFixture):
    normal_count = 2

    def test_triple(self):
        normal1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        many = normal1.manyrels.create(name="many1")
        
        with LanguageOverride('en'):
            # Get the Normal objects associated with the Many object "many1":
            normals = Normal.objects.language().filter(manyrels__id=many.pk).order_by("translated_field")
            self.assertEqual([n.pk for n in normals], [normal1.pk])
            
            # Same thing, another way:
            normals = many.normals.language()
            self.assertEqual([normal1.pk], [n.pk for n in normals])
            normals_plain = many.normals.all()
            self.assertEqual([normal1.pk], [n.pk for n in normals_plain])

    def test_manager(self):
        normal1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        simplerel = SimpleRelated.objects.language('en').create(
            normal=normal1, translated_field='test1'
        )
        with LanguageOverride('en'):
            self.assertEqual(simplerel.manynormals.count(), 0)
            simplerel.manynormals.add(normal1)
            self.assertEqual(simplerel.manynormals.count(), 1)
            self.assertEqual(simplerel.manynormals.language().get().shared_field, NORMAL[1].shared_field)

            simplerel.manynormals.clear()
            self.assertEqual(simplerel.manynormals.count(), 0)

            normal2 = simplerel.manynormals.create(
                shared_field='shared_test', translated_field='test2'
            )
            self.assertEqual(simplerel.manynormals.count(), 1)
            self.assertEqual(simplerel.manynormals.language().get().shared_field, 'shared_test')

            simplerel.manynormals.remove(normal2)
            self.assertEqual(simplerel.manynormals.count(), 0)

    def test_reverse_manager(self):
        normal1 = Normal.objects.language('en').get(pk=self.normal_id[1])
        simplerel = SimpleRelated.objects.language('en').create(
            normal=normal1, translated_field='test1'
        )
        with LanguageOverride('en'):
            self.assertEqual(normal1.manysimplerel.count(), 0)
            normal1.manysimplerel.add(simplerel)
            self.assertEqual(normal1.manysimplerel.count(), 1)
            self.assertEqual(normal1.manysimplerel.language().get().translated_field, 'test1')

            normal1.manysimplerel.clear()
            self.assertEqual(normal1.manysimplerel.count(), 0)

            simplerel2 = normal1.manysimplerel.create(
                normal=normal1, translated_field='test2'
            )
            self.assertEqual(normal1.manysimplerel.count(), 1)
            self.assertEqual(normal1.manysimplerel.language().get().translated_field, 'test2')

            normal1.manysimplerel.remove(simplerel2)
            self.assertEqual(normal1.manysimplerel.count(), 0)


class ForwardDeclaringForeignKeyTests(HvadTestCase):
    def test_issue_22(self):
        class ForwardRelated(TranslatableModel):
            shared_field = models.CharField(max_length=255)
            translations = TranslatedFields(
                translated = models.ForeignKey("ReverseRelated", related_name='rel', null=True),
            )
        
        
        class ReverseRelated(TranslatableModel):
            shared_field = models.CharField(max_length=255)
        
            translated_fields = TranslatedFields(
                translated = models.CharField(max_length=1)
            )
    def test_issue_22_non_translatable_model(self):
        class ForwardRelated2(models.Model):
            shared_field = models.CharField(max_length=255)
            fk = models.ForeignKey("ReverseRelated2", related_name='rel', null=True)
        
        
        class ReverseRelated2(TranslatableModel):
            shared_field = models.CharField(max_length=255)
        
            translated_fields = TranslatedFields(
                translated = models.CharField(max_length=1)
            )


class SelectRelatedTests(HvadTestCase, NormalFixture):
    normal_count = 2

    def create_fixtures(self):
        super(SelectRelatedTests, self).create_fixtures()
        with LanguageOverride('en'):
            self.normal1 = Normal.objects.language().get(pk=self.normal_id[1])
            self.normal2 = Normal.objects.language().get(pk=self.normal_id[2])
            SimpleRelated.objects.language().create(normal=self.normal1, translated_field="test1")

    def test_select_related_semantics(self):
        qs = Related.objects.language()
        self.assertCountEqual(qs._hvad_select_related, [])
        qs = qs.select_related('normal')
        self.assertCountEqual(qs._hvad_select_related, ['normal'])
        qs = qs.select_related('translated')
        if django.VERSION >= (1, 7):
            self.assertCountEqual(qs._hvad_select_related, ['normal', 'translated'])
        else:
            self.assertCountEqual(qs._hvad_select_related, ['translated'])
        qs = qs.select_related(None)
        self.assertCountEqual(qs._hvad_select_related, [])

    def test_select_related(self):
        with LanguageOverride('en'):  
            SimpleRelated.objects.language().create(normal=self.normal2, translated_field="test2")

            with self.assertNumQueries(1):
                rel_objects = SimpleRelated.objects.language().select_related('normal').order_by('normal__shared_field')

                check = [
                    (NORMAL[1].shared_field, NORMAL[1].translated_field['en']),
                    (NORMAL[2].shared_field, NORMAL[2].translated_field['en']),
                ]
                self.assertEqual(list((obj.normal.shared_field, obj.normal.translated_field)
                                      for obj in rel_objects),
                                 check)

    def test_select_related_cleans_cache(self):
        with LanguageOverride('en'):
            rel_objects = SimpleRelated.objects.language().select_related('normal')
            cache = getattr(Normal, Normal._meta.translations_accessor).related.get_cache_name()
            self.assertFalse(hasattr(rel_objects[0].normal, cache))

    def test_select_related_using_get(self):
        with LanguageOverride('en'):  
            with self.assertNumQueries(1):
                r = SimpleRelated.objects.language().select_related('normal').get(translated_field="test1")
                self.assertEqual(r.normal.pk, self.normal_id[1])
                self.assertEqual(self.normal1.shared_field, r.normal.shared_field)
                self.assertEqual(self.normal1.translated_field, r.normal.translated_field)
                
    def test_select_related_from_translated_field(self):
        with LanguageOverride('en'):
            Related.objects.language().create(pk=1, translated=self.normal1).save()
            with self.assertNumQueries(1):
                r = Related.objects.language().select_related('translated').get(translated=self.normal1)
                self.assertEqual(r.translated.pk, self.normal_id[1])
                self.assertEqual(self.normal1.shared_field, r.translated.shared_field)
                self.assertEqual(self.normal1.translated_field, r.translated.translated_field)

    def test_select_related_with_null_relation(self):
        with LanguageOverride('en'):
            # First, two Normal objects are created by TwoTranslatedNormalMixin (in English and Japanese)
            related1 = Related.objects.language().create(normal=self.normal1, translated=self.normal1)
            # Now we create another, but with relations set to None:
            related2 = Related.objects.language().create(normal=None, translated=None)

            with self.assertNumQueries(1):
                rel_objects = Related.objects.language().select_related('normal', 'translated')
                #print(rel_objects.query) # Note: uncommenting this line causes the test to fail, which shouldn't happen :-()
                self.assertEqual(len(rel_objects), 2)
                for r in rel_objects:
                    if (r.id == related1.id):
                        self.assertEqual(self.normal1.translated_field, r.normal.translated_field)
                        self.assertEqual(self.normal1.translated_field, r.translated.translated_field)
                    elif (r.id == related2.id):
                        self.assertEqual(r.normal, None)
                        self.assertEqual(r.translated, None)
                    else:
                        self.fail("Invalid Related object; ID is %s" % r.id)

class DeepSelectRelatedTests(HvadTestCase, StandardFixture, NormalFixture):
    normal_count = 2
    standard_count = 1

    def create_fixtures(self):
        super(DeepSelectRelatedTests, self).create_fixtures()
        with LanguageOverride('en'):
            self.normal1 = Normal.objects.language().get(pk=self.normal_id[1])
            self.normal2 = Normal.objects.language().get(pk=self.normal_id[2])
            self.standard1 = Standard.objects.get(pk=self.standard_id[1])

            self.simplerel = SimpleRelated.objects.language().create(
                normal=self.normal1, translated_field="test1"
            )
            self.related1 = Related.objects.language().create(
                normal=self.normal1, translated=self.normal2
            )
            self.related2 = Related.objects.language().create(
                normal=self.normal2, translated=self.normal1
            )
            self.relrel1 = RelatedRelated.objects.language().create(
                related=self.related1, simple=self.simplerel,
                trans_related=self.related2, trans_simple=None
            )
            self.relrel2 = RelatedRelated.objects.language().create(
                related=self.related2, simple=None,
                trans_related=self.related1, trans_simple=self.simplerel
            )
            self.standardrel1 = StandardRelated.objects.language().create(
                shared_field='shared1', translated_field='translated1',
                standard=self.standard1
            )

    def test_deep_select_related(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                qs = RelatedRelated.objects.language().select_related('related__normal', 'simple__normal')
                self.assertCountEqual((obj.pk for obj in qs),
                                      (self.relrel1.pk, self.relrel2.pk))
            with self.assertNumQueries(0):
                for obj in qs:
                    if obj.pk == self.relrel1.pk:
                        self.assertEqual(obj.related.pk, self.related1.pk)
                        self.assertEqual(obj.related.normal.pk, self.normal_id[1])
                        self.assertEqual(obj.related.normal.translated_field,
                                         NORMAL[1].translated_field['en'])
                        self.assertEqual(obj.simple.pk, self.simplerel.pk)
                        self.assertEqual(obj.simple.translated_field,
                                         self.simplerel.translated_field)
                        self.assertEqual(obj.simple.normal.pk, self.normal_id[1])
                        self.assertEqual(obj.simple.normal.translated_field,
                                         NORMAL[1].translated_field['en'])
                    if obj.pk == self.relrel2.pk:
                        self.assertEqual(obj.related.pk, self.related2.pk)
                        self.assertEqual(obj.related.normal.pk, self.normal_id[2])
                        self.assertEqual(obj.related.normal.translated_field,
                                         NORMAL[2].translated_field['en'])
                        self.assertEqual(obj.simple, None)

    def test_deep_select_related_through_vanilla(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                obj = (StandardRelated.objects.language()
                                              .select_related('standard__normal')
                                              .get(pk=self.standardrel1.pk))
            with self.assertNumQueries(0):
                self.assertEqual(obj.standard.pk, self.standard_id[1])
                self.assertEqual(obj.standard.normal.pk, self.normal_id[STANDARD[1].normal])


    def test_deep_select_related_using_get(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                obj = (RelatedRelated.objects.language()
                                             .select_related('related__normal', 'simple__normal')
                                             .get(pk=self.relrel1.pk))
            with self.assertNumQueries(0):
                self.assertEqual(obj.related.pk, self.related1.pk)
                self.assertEqual(obj.related.normal.pk, self.normal_id[1])
                self.assertEqual(obj.related.normal.translated_field,
                                 NORMAL[1].translated_field['en'])
                self.assertEqual(obj.simple.pk, self.simplerel.pk)
                self.assertEqual(obj.simple.translated_field,
                                 self.simplerel.translated_field)
                self.assertEqual(obj.simple.normal.pk, self.normal_id[1])
                self.assertEqual(obj.simple.normal.translated_field,
                                 NORMAL[1].translated_field['en'])

    def test_deep_select_related_from_translated_field(self):
        with LanguageOverride('en'):
            with self.assertNumQueries(1):
                qs = RelatedRelated.objects.language().select_related( 'trans_related__normal', 'trans_simple__normal')
                self.assertCountEqual((obj.pk for obj in qs),
                                      (self.relrel1.pk, self.relrel2.pk))
            with self.assertNumQueries(0):
                for obj in qs:
                    if obj.pk == self.relrel1.pk:
                        self.assertEqual(obj.trans_related.pk, self.related2.pk)
                        self.assertEqual(obj.trans_related.normal.pk, self.normal_id[2])
                        self.assertEqual(obj.trans_related.normal.translated_field,
                                         NORMAL[2].translated_field['en'])
                        self.assertEqual(obj.trans_simple, None)
                    if obj.pk == self.relrel2.pk:
                        self.assertEqual(obj.trans_related.pk, self.related1.pk)
                        self.assertEqual(obj.trans_related.normal.pk, self.normal_id[1])
                        self.assertEqual(obj.trans_related.normal.translated_field,
                                         NORMAL[1].translated_field['en'])
                        self.assertEqual(obj.trans_simple.pk, self.simplerel.pk)
                        self.assertEqual(obj.trans_simple.translated_field,
                                         self.simplerel.translated_field)
                        self.assertEqual(obj.trans_simple.normal.pk, self.normal_id[1])
                        self.assertEqual(obj.trans_simple.normal.translated_field,
                                         NORMAL[1].translated_field['en'])
