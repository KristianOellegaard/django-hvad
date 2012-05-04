# -*- coding: utf-8 -*-
from hvad.admin import TranslatableModelAdminMixin
from hvad.forms import translatable_inlineformset_factory
from hvad.forms import TranslatableModelForm, TranslatableModelFormMetaclass
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import NaniTestCase
from hvad.test_utils.request_factory import RequestFactory
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