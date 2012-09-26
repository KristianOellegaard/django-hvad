# -*- coding: utf-8 -*-
from hvad.test_utils.testcase import NaniTestCase
from hvad.test_utils.project.app.models import Normal, NormalProxy, NormalProxyProxy


class ProxyTests(NaniTestCase):
    def test_proxy(self):
        self.assertEqual(NormalProxy.objects.count(), 0)
        self.assertEqual(NormalProxy.objects.language('en').count(), 0)

        # creation
        Normal.objects.language('en').create(shared_field='SHARED', translated_field='English')
        self.assertEqual(NormalProxy.objects.language('en').count(), 1)

        NormalProxy.objects.language('en').create(shared_field='SHARED2', translated_field='English2')
        self.assertEqual(NormalProxy.objects.language('en').count(), 2)

        NormalProxy.objects.language('jp').create(shared_field='JPSHARED3', translated_field='Japanese')
        self.assertEqual(NormalProxy.objects.language('jp').count(), 1)

        # filter
        self.assertEqual(NormalProxy.objects.filter(shared_field__startswith='SHARED').count(), 2)
        self.assertEqual(NormalProxy.objects.language('en').filter(translated_field__startswith='English').count(), 2)
        self.assertEqual(NormalProxy.objects.language('en').filter(translated_field='English').count(), 1)

    def test_proxy_proxy(self):
        self.assertEqual(NormalProxyProxy.objects.language('en').count(), 0)

        # creation
        NormalProxyProxy.objects.language('en').create(shared_field='SHARED', translated_field='English')
        self.assertEqual(NormalProxyProxy.objects.language('en').count(), 1)

    def test_translation_queryset(self):
        NormalProxy.objects.language('en').create(shared_field='SHARED2', translated_field='English2')
        self.assertTrue(isinstance(Normal.objects.language('en').get(), Normal))
        self.assertFalse(isinstance(Normal.objects.language('en').get(), NormalProxy))
        self.assertTrue(isinstance(NormalProxy.objects.language('en').get(), NormalProxy))
        self.assertFalse(isinstance(NormalProxy.objects.language('en').get(), NormalProxyProxy))
        self.assertTrue(isinstance(NormalProxyProxy.objects.language('en').get(), NormalProxyProxy))

    def test_fallback_queryset(self):
        NormalProxyProxy.objects.language('en').create(shared_field='SHARED2', translated_field='English2')
        self.assertTrue(isinstance(Normal.objects.untranslated().use_fallbacks().get(), Normal))
        self.assertFalse(isinstance(Normal.objects.untranslated().use_fallbacks().get(), NormalProxy))
        self.assertTrue(isinstance(NormalProxy.objects.untranslated().use_fallbacks().get(), NormalProxy))
        self.assertFalse(isinstance(NormalProxy.objects.untranslated().use_fallbacks().get(), NormalProxyProxy))
        self.assertTrue(isinstance(NormalProxyProxy.objects.untranslated().use_fallbacks().get(), NormalProxyProxy))
