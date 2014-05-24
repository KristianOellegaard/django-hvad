# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from hvad.test_utils.data import DOUBLE_NORMAL, D1, D3, D2
from hvad.test_utils.project.app.models import Normal, Date, Standard, ConcreteAB


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


class TwoTranslatedConcreteABMixin(TwoTranslatedNormalMixin):
    def create_fixtures(self):
        super(TwoTranslatedConcreteABMixin, self).create_fixtures()
        normal1 = Normal.objects.language('en').get(shared_field='Shared1')
        normal2 = Normal.objects.language('en').get(shared_field='Shared2')

        ab1 = ConcreteAB.objects.language('en').create(
            shared_field_a = DOUBLE_NORMAL[1]['shared_field'],
            shared_field_b = normal1,
            shared_field_ab = DOUBLE_NORMAL[1]['shared_field'],
            translated_field_a = normal1,
            translated_field_b = DOUBLE_NORMAL[1]['translated_field_en'],
            translated_field_ab = DOUBLE_NORMAL[1]['translated_field_en'],
        )
        ab1.translate('ja')
        ab1.translated_field_a = normal2
        ab1.translated_field_b = DOUBLE_NORMAL[1]['translated_field_ja']
        ab1.translated_field_ab = DOUBLE_NORMAL[1]['translated_field_ja']
        ab1.save()

        ab2 = ConcreteAB.objects.language('ja').create(
            shared_field_a = DOUBLE_NORMAL[2]['shared_field'],
            shared_field_b = normal2,
            shared_field_ab = DOUBLE_NORMAL[2]['shared_field'],
            translated_field_a = normal2,
            translated_field_b = DOUBLE_NORMAL[2]['translated_field_ja'],
            translated_field_ab = DOUBLE_NORMAL[2]['translated_field_ja'],
        )
        ab2.translate('en')
        ab2.translated_field_a = normal1
        ab2.translated_field_b = DOUBLE_NORMAL[2]['translated_field_en']
        ab2.translated_field_ab = DOUBLE_NORMAL[2]['translated_field_en']
        ab2.save()

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
