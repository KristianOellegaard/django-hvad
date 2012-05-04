# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User

from hvad.test_utils.testcase import NaniTestCase
from hvad.test_utils.fixtures import TwoTranslatedNormalMixin

from testproject.app.models import LimitedChoice


class LimitChoicesToTests(NaniTestCase, TwoTranslatedNormalMixin):
    def create_fixtures(self):
        su = User(
            email='admin@admin.com',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            username='admin',
        )
        su.set_password('admin')
        su.save()
        self.user = su
        super(LimitChoicesToTests, self).create_fixtures()

    def test_limit_choices_to(self):
        """
        Checks if limit_choices_to works on ForeignKey and ManyToManyField.
        """

        limited_choice_admin = admin.site._registry[LimitedChoice]
        
        with self.login_user_context(
            username='admin',
            password='admin'
        ):
            rf = self.request_factory
            get_request = rf.get('/admin/app/limitedchoice/add')
            
            # We need to attach the client's session to the request,
            # otherwise admin won't let us in 
            get_request.session = self.client.session 

            # in django 1.4 request.user is required
            get_request.user = self.user

            # Let's construct the relevant admin form...
            Form = limited_choice_admin.get_form(get_request)
            form = Form()

            # ...and see if the ForeignKey field's queryset contains valid
            # choices only.
            qs_fk = form.fields['choice_fk'].queryset
            self.assertTrue(qs_fk.filter(shared_field='Shared1').exists())
            self.assertFalse(qs_fk.filter(shared_field='Shared2').exists())


            # Now do the same for the ManyToManyField.
            qs_mm = form.fields['choice_mm'].queryset
            self.assertTrue(qs_mm.filter(shared_field='Shared2').exists())
            self.assertFalse(qs_mm.filter(shared_field='Shared1').exists())

