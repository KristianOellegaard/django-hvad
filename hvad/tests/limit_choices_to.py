from django.contrib import admin
from django.contrib.auth.models import User

from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.fixtures import NormalFixture, UsersFixture

from hvad.test_utils.project.app.models import LimitedChoice


class LimitChoicesToTests(HvadTestCase, UsersFixture, NormalFixture):
    normal_count = 2

    def test_limit_choices_to(self):
        """
        Checks if limit_choices_to works on ForeignKey and ManyToManyField.
        """

        limited_choice_admin = admin.site._registry[LimitedChoice]

        with self.login_user_context('admin'):
            rf = self.request_factory
            get_request = rf.get('/admin/app/limitedchoice/add')

            # We need to attach the client's session to the request,
            # otherwise admin won't let us in 
            get_request.session = self.client.session 
            get_request.user = User.objects.get(pk=self.user_id['admin'])

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

