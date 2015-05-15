# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from hvad.test_utils.data import USER, NORMAL, STANDARD, CONCRETEAB, DATE, QONORMAL
from hvad.test_utils.project.app.models import Normal, Standard, ConcreteAB, Date, QONormal

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


class UsersFixture(Fixture):
    def create_fixtures(self):
        super(UsersFixture, self).create_fixtures()

        self.user_id = {}
        for user in USER:
            self.user_id[user['username']] = self.create_user(user).pk

    def create_user(self, data):
        kwargs = data.copy()
        kwargs.setdefault('email', '%s@hvad.com' % kwargs['username'])
        kwargs.setdefault('is_superuser', False)
        kwargs.setdefault('is_staff', kwargs['is_superuser'])
        obj = User(**kwargs)
        obj.set_password(data['username'])
        obj.save()
        return obj

