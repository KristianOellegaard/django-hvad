# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from hvad.test_utils.data import NORMAL, STANDARD, RELATED, CONCRETEAB, DATE, QONORMAL
from hvad.test_utils.project.app.models import (Normal, Standard, Related, ConcreteAB,
                                                Date, QONormal)


class Fixture(object):
    translations = ('en', 'ja')
    def create_fixtures(self):
        pass

#===============================================================================

class NormalFixture(Fixture):
    normal_count = 0

    def create_fixtures(self):
        super(NormalFixture, self).create_fixtures()
        assert self.normal_count <= len(NORMAL), 'Not enough fixtures in data'

        self.normal_id = {}
        for i in range(1, self.normal_count + 1):
            self.normal_id[i] = self.create_normal(NORMAL[i]).pk

    def create_normal(self, data, translations=None):
        obj = Normal(shared_field=data.shared_field)
        for code in translations or self.translations:
            obj.translate(code)
            obj.translated_field = data.translated_field[code]
            obj.save()
        return obj


class StandardFixture(NormalFixture):
    standard_count = 0

    def create_fixtures(self):
        super(StandardFixture, self).create_fixtures()
        assert self.standard_count <= len(STANDARD)

        self.standard_id = {}
        for i in range(1, self.standard_count + 1):
            self.standard_id[i] = self.create_standard(STANDARD[i]).pk

    def create_standard(self, data):
        obj = Standard.objects.create(
            normal_field=data.normal_field,
            normal_id=self.normal_id[data.normal],
        )
        return obj


class RelatedFixture(NormalFixture):
    related_count = 0

    def create_fixtures(self):
        super(RelatedFixture, self).create_fixtures()
        assert self.related_count <= len(RELATED)

        self.related_id = {}
        for i in range(1, self.related_count + 1):
            self.related_id[i] = self.create_related(RELATED[i]).pk

    def create_related(self, data, translations=None):
        obj = Related(normal_id=self.normal_id[data.normal])
        for code in translations or self.translations:
            obj.translate(code)
            obj.translated_id = self.normal_id[data.translated[code]]
            obj.translated_to_translated_id = self.normal_id[data.translated_to_translated[code]]
            obj.save()
        return obj


class QONormalFixture(Fixture):
    qonormal_count = 0

    def create_fixtures(self):
        super(QONormalFixture, self).create_fixtures()
        assert self.qonormal_count <= len(QONORMAL), 'Not enough fixtures in data'

        self.qonormal_id = {}
        for i in range(1, self.qonormal_count + 1):
            self.qonormal_id[i] = self.create_qonormal(QONORMAL[i]).pk

    def create_qonormal(self, data, translations=None):
        obj = QONormal(shared_field=data.shared_field)
        for code in translations or self.translations:
            obj.translate(code)
            obj.translated_field = data.translated_field[code]
            obj.save()
        return obj


class ConcreteABFixture(NormalFixture):
    concreteab_count = 0

    def create_fixtures(self):
        super(ConcreteABFixture, self).create_fixtures()
        assert self.concreteab_count <= len(CONCRETEAB)

        self.concreteab_id = {}
        for i in range(1, self.concreteab_count + 1):
            self.concreteab_id[i] = self.create_concreteab(CONCRETEAB[i]).pk

    def create_concreteab(self, data, translations=None):
        obj = ConcreteAB(
            shared_field_a=data.shared_field_a,
            shared_field_b_id=self.normal_id[data.shared_field_b],
            shared_field_ab=data.shared_field_ab,
        )
        for code in translations or self.translations:
            obj.translate(code)
            obj.translated_field_a_id = self.normal_id[data.translated_field_a[code]]
            obj.translated_field_b = data.translated_field_b[code]
            obj.translated_field_ab = data.translated_field_ab[code]
            obj.save()
        return obj


class DateFixture(Fixture):
    date_count = 0

    def create_fixtures(self):
        super(DateFixture, self).create_fixtures()
        assert self.date_count <= len(DATE)

        self.date_id = {}
        for i in range(1, self.date_count + 1):
            self.date_id[i] = self.create_date(DATE[i]).pk

    def create_date(self, data, translations=None):
        obj = Date(shared_date=data.shared_date)
        for code in translations or self.translations:
            obj.translate(code)
            obj.translated_date = data.translated_date[code]
            obj.save()
        return obj


class SuperuserFixture(Fixture):
    def create_fixtures(self):
        super(SuperuserFixture, self).create_fixtures()

        su = User(
            email='admin@admin.com',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            username='admin',
        )
        su.set_password('admin')
        su.save()
        self.superuser = su
