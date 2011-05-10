# -*- coding: utf-8 -*-
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase
from testproject.app.models import Normal, Related, Standard, Other

class OrderingTest(NaniTestCase):
    def test_minus_order_by(self):
        with LanguageOverride("en"):
            obj = Normal(language_code='en', translated_field = "English", shared_field="lol")
            obj.save()
            self.assertEqual(Normal.objects.order_by('-shared_field').count(), len(Normal.objects.order_by('-shared_field')))