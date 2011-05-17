# -*- coding: utf-8 -*-
from datetime import datetime
from django.contrib.auth.models import User
from nani.test_utils.data import D1, D3, D2
from testproject.app.models import Normal, Date, Standard


class Fixture(object):
    def create_fixtures(self):
        pass


class OneSingleTranslatedNormalMixin(Fixture):
    def create_fixtures(self):
        Normal.objects.language('en').create(
            shared_field='shared',
            translated_field='English'
        )
        super(OneSingleTranslatedNormalMixin, self).create_fixtures()


class TwoTranslatedNormalMixin(Fixture):
    def create_fixtures(self):
        en1 = Normal.objects.language('en').create(
            shared_field = 'Shared1',
            translated_field = 'English1',
        )
        ja1 = en1.translate('ja')
        ja1.translated_field = u'日本語一'
        ja1.save()
        
        en2 = Normal.objects.language('en').create(
            shared_field = 'Shared2',
            translated_field = 'English2',
        )
        ja2 = en2.translate('ja')
        ja2.translated_field = u'日本語二'
        ja2.save()
        super(TwoTranslatedNormalMixin, self).create_fixtures()


class SuperuserMixin(Fixture):
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
        super(SuperuserMixin, self).create_fixtures()


class DatesMixin(Fixture):
    def create_fixtures(self):
        en1 = Date.objects.language('en').create(shared_date=D1,
                                                translated_date=D3)
        ja1 = en1.translate('ja')
        ja1.translated_date = D2
        ja1.save()
        en2 = Date.objects.language('en').create(shared_date=D3,
                                                translated_date=D2)
        ja2 = en2.translate('ja')
        ja2.translated_date = D1
        ja2.save()
        en3 = Date.objects.language('en').create(shared_date=D2,
                                                translated_date=D1)
        ja3 = en3.translate('ja')
        ja3.translated_date = D3
        ja3.save()
        super(DatesMixin, self).create_fixtures()

class TwoNormalOneStandardMixin(Fixture):
    def create_fixtures(self):
        en = Normal.objects.language('en').create(
            shared_field='shared',
            translated_field='English'
        )
        ja = en.translate('ja')
        ja.translated_field = u'日本語'
        ja.save()
        Standard.objects.create(normal_field="normal", normal=en) 
        super(TwoNormalOneStandardMixin, self).create_fixtures()
