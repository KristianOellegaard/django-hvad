# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from hvad.test_utils.context_managers import LanguageOverride
from hvad.test_utils.testcase import NaniTestCase
from hvad.test_utils.request_factory import RequestFactory
from testproject.app.models import Normal, Related
from hvad.views import TranslatableUpdateView

class ViewsTest(NaniTestCase):
    def setUp(self):
        with LanguageOverride("en"):
            self.object = Normal.objects.language().create(shared_field="test", translated_field="translated test")

            self.rf = RequestFactory()
            self.request = self.rf.post('/url/')

    def test_update_view_get(self):
        with LanguageOverride("en"):
            response = self.client.get(reverse('update_normal', args=[self.object.id]))
            self.assertTrue(response.status_code== 200)

            response = self.client.get(reverse('update_normal_slug', kwargs={'slug': self.object.shared_field}))
            self.assertTrue(response.status_code == 200)

            response = self.client.get(reverse('update_normal', args=[self.object.id]) + "?%s=da" % TranslatableUpdateView.query_language_key)
            self.assertTrue(response.status_code == 200)

            response = self.client.get(reverse('update_normal', args=[self.object.id * 100]) + "?%s=da" % TranslatableUpdateView.query_language_key)
            self.assertTrue(response.status_code == 404)

    def test_update_view_post(self):
        with LanguageOverride("en"):
            translated_string = u"some english translation"
            response = self.client.post(reverse('update_normal', args=[self.object.id]),
                                                data={
                                                    'shared_field': 'some value',
                                                    'translated_field': translated_string,
                                                })
            self.assertTrue(response.status_code == 302)
            obj = Normal.objects.language().filter(pk=self.object.id).get()
            self.assertTrue(obj.translated_field == translated_string)


            translated_string = u"svenne banan æøå"
            response = self.client.post(reverse('update_normal', args=[self.object.id]) + "?%s=da" % TranslatableUpdateView.query_language_key,data={
                                                    'shared_field': 'some value',
                                                    'translated_field': translated_string,
                                                })
            self.assertTrue(response.status_code, 200)
            obj = Normal.objects.language("da").filter(pk=self.object.id).get()
            self.assertTrue(obj.translated_field == translated_string)