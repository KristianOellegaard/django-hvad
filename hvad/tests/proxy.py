# -*- coding: utf-8 -*-
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal, NormalProxy, NormalProxyProxy, RelatedProxy, SimpleRelatedProxy


class ProxyTests(HvadTestCase):
    def test_check(self):
        self.assertEqual(len(NormalProxy.check()), 0)
        self.assertEqual(len(NormalProxyProxy.check()), 0)
        self.assertEqual(len(RelatedProxy.check()), 0)
        self.assertEqual(len(SimpleRelatedProxy.check()), 0)

    def test_proxy(self):
        self.assertEqual(NormalProxy.objects.count(), 0)
        self.assertEqual(NormalProxy.objects.language('en').count(), 0)

        # creation
        normal = Normal.objects.language('en').create(shared_field='SHARED', translated_field='English')
        self.assertEqual(NormalProxy.objects.language('en').count(), 1)

        NormalProxy.objects.language('en').create(shared_field='SHARED2', translated_field='English2')
        self.assertEqual(NormalProxy.objects.language('en').count(), 2)

        NormalProxy.objects.language('jp').create(shared_field='JPSHARED3', translated_field='Japanese')
        self.assertEqual(NormalProxy.objects.language('jp').count(), 1)

        # filter
        self.assertEqual(NormalProxy.objects.filter(shared_field__startswith='SHARED').count(), 2)
        self.assertEqual(NormalProxy.objects.language('en').filter(translated_field__startswith='English').count(), 2)
        self.assertEqual(NormalProxy.objects.language('en').filter(translated_field='English').count(), 1)

        # select_related
        RelatedProxy.objects.language('en').create(normal=normal)
            # does it work?
        self.assertEqual(RelatedProxy.objects.language('en').select_related('normal').count(), 1)
            # does it actually cache stuff?
        normal_cache = RelatedProxy._meta.get_field('normal').get_cache_name()
        self.assertTrue(isinstance(getattr(RelatedProxy.objects.language('en').select_related('normal').get(), normal_cache), Normal))

    def test_proxy_proxy(self):
        self.assertEqual(NormalProxyProxy.objects.language('en').count(), 0)

        # creation
        NormalProxyProxy.objects.language('en').create(shared_field='SHARED', translated_field='English')
        self.assertEqual(NormalProxyProxy.objects.language('en').count(), 1)

    def test_proxy_simple_relation(self):
        self.assertEqual(NormalProxy.objects.count(), 0)
        self.assertEqual(NormalProxy.objects.language('en').count(), 0)

        NormalProxy.objects.language('en').create(shared_field='SHARED', translated_field='English')
        normal = NormalProxy.objects.get(shared_field='SHARED')
        SimpleRelatedProxy.objects.language('en').create(normal=normal, translated_field='RelatedEnglish')

        from hvad.utils import get_translation_aware_manager
        srp_manager = get_translation_aware_manager(SimpleRelatedProxy)
        qs = srp_manager.language('en').filter(normal__translated_field='English')
        self.assertEqual(qs.count(), 1)
        np_manager = get_translation_aware_manager(NormalProxy)
        qs = np_manager.language('en').filter(simplerel__translated_field='RelatedEnglish')
        self.assertEqual(qs.count(), 1)

    def test_translation_queryset(self):
        NormalProxy.objects.language('en').create(shared_field='SHARED2', translated_field='English2')
        self.assertTrue(isinstance(Normal.objects.language('en').get(), Normal))
        self.assertFalse(isinstance(Normal.objects.language('en').get(), NormalProxy))
        self.assertTrue(isinstance(NormalProxy.objects.language('en').get(), NormalProxy))
        self.assertFalse(isinstance(NormalProxy.objects.language('en').get(), NormalProxyProxy))
        self.assertTrue(isinstance(NormalProxyProxy.objects.language('en').get(), NormalProxyProxy))
