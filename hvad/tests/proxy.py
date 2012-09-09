# -*- coding: utf-8 -*-
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal, NormalProxy


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
