# -*- coding: utf-8 -*-
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import SingleNormalTestCase, NaniTestCase
from testproject.app.models import Normal, Related


class NormalToNormalFKTest(SingleNormalTestCase):
    def test_relation(self):
        normal = self.get_obj()
        related = Related.objects.create(normal=normal)
        self.assertEqual(related.normal.pk, normal.pk)
        self.assertEqual(related.normal.shared_field, normal.shared_field)
        self.assertEqual(related.normal.translated_field, normal.translated_field)
        self.assertTrue(related in normal.rel1.all())


class NormalToTransFKTest(SingleNormalTestCase):
    def test_relation(self):
        en = self.get_obj()
        ja = en
        ja.language_code = 'ja'
        ja.translated_field = u'何'
        ja.save()
        self.assertEqual(Normal._meta.translations_model.objects.count(), 2)
        related = Related.objects.create(normal_trans=ja)
        with LanguageOverride('en'):
            related = self.reload(related)
            self.assertEqual(related.normal_trans.pk, ja.pk)
            self.assertEqual(related.normal_trans.shared_field, ja.shared_field)
            self.assertEqual(related.normal_trans.translated_field, ja.translated_field)
            self.assertTrue(related in ja.rel2.all())


class TransToNormalFKTest(NaniTestCase):
    pass


class TransToTransFKTest(NaniTestCase):
    pass