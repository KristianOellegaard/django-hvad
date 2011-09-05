# -*- coding: utf-8 -*-
from nani.admin import TranslatableModelAdminMixin
from nani.forms import translatable_inlineformset_factory
from nani.forms import TranslatableModelForm, TranslatableModelFormMetaclass
from nani.test_utils.context_managers import LanguageOverride
from nani.test_utils.testcase import NaniTestCase
from nani.test_utils.request_factory import RequestFactory
from testproject.app.models import Normal, Related
from django.db import models

class TestBasicInline(NaniTestCase):
    def setUp(self):
        with LanguageOverride("en"):
            self.object = Normal.objects.language().create(shared_field="test", translated_field="translated test")
            rf = RequestFactory()
            self.request = rf.post('/url/')

    def test_create_fields_inline(self):
        with LanguageOverride("en"):
            # Fixtures (should eventually be shared with other tests)

            translate_mixin = TranslatableModelAdminMixin()
            formset = translatable_inlineformset_factory(translate_mixin._language(self.request),
                                                         Normal, Related)(#self.request.POST,
                                                                          instance=self.object)

            self.assertTrue(formset.forms[0].fields.has_key("normal"))
            self.assertTrue(formset.forms[0].fields.has_key("translated"))
            self.assertTrue(formset.forms[0].fields.has_key("translated_to_translated"))
            self.assertFalse(formset.forms[0].fields.has_key("language_code"))