# -*- coding: utf-8 -*-
from django.utils import translation
from hvad.test_utils.data import QONORMAL
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import QONormal, QOSimpleRelated, QOMany
from hvad.test_utils.fixtures import QONormalFixture
from hvad.manager import TranslationQueryset


class BasicTests(HvadTestCase):
    def test_queryset_class(self):
        self.assertIsInstance(QONormal.objects.all(), TranslationQueryset)
        self.assertIsInstance(QONormal.objects.language(), TranslationQueryset)
        self.assertNotIsInstance(QONormal.objects.untranslated(), TranslationQueryset)
        self.assertIs(QONormal._default_manager, QONormal.objects)

        self.assertIsInstance(QOSimpleRelated.objects.all(), TranslationQueryset)
        self.assertIsInstance(QOSimpleRelated.objects.language(), TranslationQueryset)
        self.assertNotIsInstance(QOSimpleRelated.objects.untranslated(), TranslationQueryset)
        self.assertIs(QOSimpleRelated._default_manager, QOSimpleRelated.objects)

        self.assertIsInstance(QOMany.objects.all(), TranslationQueryset)
        self.assertIsInstance(QOMany.objects.language(), TranslationQueryset)
        self.assertNotIsInstance(QOMany.objects.untranslated(), TranslationQueryset)
        self.assertIs(QOMany._default_manager, QOMany.objects)


class FilterTests(HvadTestCase, QONormalFixture):
    """ Basic filter tests - should work without issue as manager is just
        as pass-through in those cases
    """
    qonormal_count = 2

    def test_simple_filter(self):
        with translation.override('en'):
            with self.assertNumQueries(2):
                qs = QONormal.objects.filter(shared_field__contains='2')
                self.assertEqual(qs.count(), 1)
                obj = qs[0]
            with self.assertNumQueries(0):
                self.assertEqual(obj.shared_field, QONORMAL[2].shared_field)
                self.assertEqual(obj.translated_field, QONORMAL[2].translated_field['en'])
        with translation.override('ja'):
            with self.assertNumQueries(2):
                qs = QONormal.objects.filter(shared_field__contains='1')
                self.assertEqual(qs.count(), 1)
                obj = qs[0]
            with self.assertNumQueries(0):
                self.assertEqual(obj.shared_field, QONORMAL[1].shared_field)
                self.assertEqual(obj.translated_field, QONORMAL[1].translated_field['ja'])

    def test_translated_filter(self):
        with translation.override('en'):
            with self.assertNumQueries(2):
                qs = QONormal.objects.filter(translated_field__contains='English').order_by('shared_field')
                self.assertEqual(qs.count(), 2)
                obj1, obj2 = qs
            with self.assertNumQueries(0):
                self.assertEqual(obj1.shared_field, QONORMAL[1].shared_field)
                self.assertEqual(obj1.translated_field, QONORMAL[1].translated_field['en'])
                self.assertEqual(obj2.shared_field, QONORMAL[2].shared_field)
                self.assertEqual(obj2.translated_field, QONORMAL[2].translated_field['en'])

    def test_deferred_language_filter(self):
        with translation.override('ja'):
            qs = QONormal.objects.filter(translated_field__contains='English').order_by('shared_field')
        with translation.override('en'):
            self.assertEqual(qs.count(), 2)
            obj1, obj2 = qs
        with translation.override('ja'):
            self.assertEqual(obj1.shared_field, QONORMAL[1].shared_field)
            self.assertEqual(obj1.translated_field, QONORMAL[1].translated_field['en'])
            self.assertEqual(obj2.shared_field, QONORMAL[2].shared_field)
            self.assertEqual(obj2.translated_field, QONORMAL[2].translated_field['en'])


class RelatedManagerTests(HvadTestCase, QONormalFixture):
    qonormal_count = 2

    def setUp(self):
        super(RelatedManagerTests, self).setUp()
        with translation.override('en'):
            self.normal1 = QONormal.objects.get(shared_field=QONORMAL[1].shared_field)
            self.normal2 = QONormal.objects.get(shared_field=QONORMAL[2].shared_field)
            self.related = QOSimpleRelated.objects.create(normal=self.normal1,
                                                          translated_field='translated1_en')
            # spurious instance to catch cases where filtering is not correct
            obj = QOSimpleRelated.objects.create(normal=self.normal2,
                                                 translated_field='dummy')
            obj.translate('ja').save()

            self.many1 = QOMany.objects.create(translated_field='translated1_en')
            self.many1.translate('ja')
            self.many1.translated_field = 'translated1_ja'
            self.many1.save()
            # spurious instance to catch cases where filtering is not correct
            obj = QOMany.objects.create(translated_field='dummy')
            obj.translate('ja').save()

    def test_forward_foreign_key(self):
        """ ForeignKey accessor should use the TranslationQueryset and fetch
            the translation when it retrieves the shared model.
        """
        with translation.override('en'):
            related = QOSimpleRelated.objects.get(pk=self.related.pk)
            self.assertEqual(related.translated_field, self.related.translated_field)

            with self.assertNumQueries(1):
                self.assertEqual(related.normal.shared_field, QONORMAL[1].shared_field)
            with self.assertNumQueries(0):
                self.assertEqual(related.normal.translated_field, QONORMAL[1].translated_field['en'])

    def test_reverse_foreign_key_query(self):
        """ Reverse foreign key should use the TranslationQueryset """
        with translation.override('en'):
            qs = list(self.normal1.simplerel.all())
            self.assertEqual(len(qs), 1)
            with self.assertNumQueries(0):
                self.assertEqual(qs[0].normal_id, self.qonormal_id[1])
                self.assertEqual(qs[0].translated_field, self.related.translated_field)

        with translation.override('ja'):
            qs = list(self.normal1.simplerel.all())
            self.assertEqual(len(qs), 0)

    def test_reverse_foreign_key_updates(self):
        """ Reverse foreign key should use the TranslationQueryset for adding/removing """
        with translation.override('en'):
            self.assertEqual(self.normal1.simplerel.count(), 1)
            self.normal1.simplerel.clear()
            self.assertEqual(self.normal1.simplerel.count(), 0)
            self.normal1.simplerel.add(self.related)
            self.assertEqual(self.normal1.simplerel.count(), 1)
            self.normal1.simplerel.remove(self.related)
            self.assertEqual(self.normal1.simplerel.count(), 0)

            self.normal1.simplerel.create(translated_field='test_en')
            self.assertEqual(self.normal1.simplerel.language('en').count(), 1)
            self.assertEqual(self.normal1.simplerel.language('ja').count(), 0)
            obj = self.normal1.simplerel.get(translated_field='test_en')
            self.assertEqual(obj.normal_id, self.normal1.pk)

    def test_forward_many_to_many_query(self):
        """ Forward side of many to many relation should use the TranslationQueryset
        """
        with translation.override('en'):
            many = QOMany.objects.get(translated_field='translated1_en')

            qs = many.normals.all()
            self.assertEqual(len(qs), 0)

            many.normals.add(self.normal1)
            qs = list(many.normals.all())
            with self.assertNumQueries(0):
                self.assertEqual(len(qs), 1)
                self.assertEqual(qs[0].shared_field, QONORMAL[1].shared_field)
                self.assertEqual(qs[0].translated_field, QONORMAL[1].translated_field['en'])

            qs = list(many.normals.filter(translated_field=QONORMAL[1].translated_field['en']))
            with self.assertNumQueries(0):
                self.assertEqual(len(qs), 1)
                self.assertEqual(qs[0].shared_field, QONORMAL[1].shared_field)
                self.assertEqual(qs[0].translated_field, QONORMAL[1].translated_field['en'])

    def test_forward_many_to_many_updates(self):
        with translation.override('en'):
            many = QOMany.objects.get(translated_field='translated1_en')

            many.normals.add(self.normal1, self.normal2)
            self.assertEqual(many.normals.count(), 2)
            many.normals.remove(self.normal2)
            self.assertEqual(many.normals.count(), 1)
            self.assertEqual(many.normals.get().pk, self.qonormal_id[1])
            obj = many.normals.create(translated_field='test_en')
            self.assertEqual(many.normals.count(), 2)
            self.assertEqual(many.normals.language('ja').count(), 1)
            self.assertEqual(list(obj.manyrels.values_list('pk', flat=True)), [many.pk])
            many.normals.clear()
            self.assertEqual(many.normals.count(), 0)

    def test_reverse_many_to_many_query(self):
        """ Reverse side of many to many relation should use the TranslationQueryset
        """
        with translation.override('en'):
            many = QOMany.objects.get(translated_field='translated1_en')
            many.normals.add(self.normal1)

            normal = QONormal.objects.get(pk=self.normal1.pk)
            qs = list(normal.manyrels.all())
            with self.assertNumQueries(0):
                self.assertEqual(len(qs), 1)
                self.assertEqual(qs[0].translated_field, 'translated1_en')

            qs = list(normal.manyrels.filter(translated_field='translated1_en'))
            with self.assertNumQueries(0):
                self.assertEqual(len(qs), 1)
                self.assertEqual(qs[0].translated_field, 'translated1_en')


class PrefetchRelatedTests(HvadTestCase, QONormalFixture):
    qonormal_count = 2

    def setUp(self):
        super(PrefetchRelatedTests, self).setUp()
        with translation.override('en'):
            self.normal1 = QONormal.objects.get(shared_field=QONORMAL[1].shared_field)
            self.normal2 = QONormal.objects.get(shared_field=QONORMAL[2].shared_field)
            self.related = QOSimpleRelated.objects.create(normal=self.normal1,
                                                          translated_field='translated1_en')
            # spurious instance to catch cases where filtering is not correct
            obj = QOSimpleRelated.objects.create(normal=self.normal2,
                                                 translated_field='dummy')
            obj.translate('ja').save()

            self.many1 = QOMany.objects.create(translated_field='translated1_en')
            self.many1.translate('ja')
            self.many1.translated_field = 'translated1_ja'
            self.many1.save()
            # spurious instance to catch cases where filtering is not correct
            obj = QOMany.objects.create(translated_field='dummy')
            obj.translate('ja').save()

    def test_reverse_foreign_key(self):
        with translation.override('en'):
            with self.assertNumQueries(2):
                obj = QONormal.objects.prefetch_related('simplerel').get(pk=self.qonormal_id[1])
            with self.assertNumQueries(0):
                self.assertEqual(len(obj.simplerel.all()), 1)
                self.assertEqual(obj.simplerel.all()[0].pk, self.related.pk)
                # this is the crucial part: translation should be cached, too
                self.assertEqual(obj.simplerel.all()[0].translated_field, 'translated1_en')

        with translation.override('ja'):
            with self.assertNumQueries(2):
                obj = QONormal.objects.prefetch_related('simplerel').get(pk=self.qonormal_id[1])
            with self.assertNumQueries(0):
                # just checking language filter is actually applied
                self.assertEqual(len(obj.simplerel.all()), 0)

    def test_forward_many_to_many(self):
        self.many1.normals.add(self.normal1)
        with translation.override('en'):
            with self.assertNumQueries(2):
                obj = QOMany.objects.prefetch_related('normals').get(pk=self.many1.pk)
            with self.assertNumQueries(0):
                self.assertEqual(len(obj.normals.all()), 1)
                self.assertEqual(obj.normals.all()[0].translated_field,
                                 QONORMAL[1].translated_field['en'])
        with translation.override('ja'):
            with self.assertNumQueries(2):
                obj = QOMany.objects.prefetch_related('normals').get(pk=self.many1.pk)
            with self.assertNumQueries(0):
                self.assertEqual(len(obj.normals.all()), 1)
                self.assertEqual(obj.normals.all()[0].translated_field,
                                 QONORMAL[1].translated_field['ja'])

    def test_reverse_many_to_many(self):
        self.many1.normals.add(self.normal1)
        with translation.override('en'):
            with self.assertNumQueries(2):
                obj = QONormal.objects.prefetch_related('manyrels').get(pk=self.qonormal_id[1])
            with self.assertNumQueries(0):
                self.assertEqual(len(obj.manyrels.all()), 1)
                self.assertEqual(obj.manyrels.all()[0].translated_field,
                                 'translated1_en')
        with translation.override('ja'):
            with self.assertNumQueries(2):
                obj = QONormal.objects.prefetch_related('manyrels').get(pk=self.qonormal_id[1])
            with self.assertNumQueries(0):
                self.assertEqual(len(obj.manyrels.all()), 1)
                self.assertEqual(obj.manyrels.all()[0].translated_field,
                                 'translated1_ja')
