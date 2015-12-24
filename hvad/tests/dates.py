from hvad.test_utils.data import DATE_REVERSED, DATE_VALUES
from hvad.test_utils.fixtures import DateFixture
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Date
import datetime

D1, D2, D3 = DATE_VALUES

class LatestTests(HvadTestCase, DateFixture):
    date_count = 3

    def test_shared_latest(self):
        latest = Date.objects.language('en').latest('shared_date')
        self.assertEqual(latest.pk, self.date_id[DATE_REVERSED[D3].shared_date])

    def test_translated_latest(self):
        latest = Date.objects.language('en').latest('translated_date')
        self.assertEqual(latest.pk, self.date_id[DATE_REVERSED[D3].translated_date['en']])
        latest = Date.objects.language('ja').latest('translated_date')
        self.assertEqual(latest.pk, self.date_id[DATE_REVERSED[D3].translated_date['ja']])

    def test_default_latest(self):
        latest = Date.objects.language('en').latest()
        self.assertEqual(latest.pk, self.date_id[DATE_REVERSED[D3].shared_date])


class EarliestTests(HvadTestCase, DateFixture):
    date_count = 3

    def test_shared_earliest(self):
        earliest = Date.objects.language('en').earliest('shared_date')
        self.assertEqual(earliest.pk, self.date_id[DATE_REVERSED[D1].shared_date])

    def test_translated_earliest(self):
        earliest = Date.objects.language('en').earliest('translated_date')
        self.assertEqual(earliest.pk, self.date_id[DATE_REVERSED[D1].translated_date['en']])
        earliest = Date.objects.language('ja').earliest('translated_date')
        self.assertEqual(earliest.pk, self.date_id[DATE_REVERSED[D1].translated_date['ja']])

    def test_default_earliest(self):
        earliest = Date.objects.language('en').earliest()
        self.assertEqual(earliest.pk, self.date_id[DATE_REVERSED[D1].shared_date])


class DatesTests(HvadTestCase, DateFixture):
    date_count = 3

    def test_objects_dates(self):
        d2011 = datetime.date(year=2011, month=1, day=1)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "year")), 2)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "year").all()), 2)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "month")), 3)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "day")), 3)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "day").filter(shared_date__gt=d2011)), 2)

class DatetimeTests(HvadTestCase, DateFixture):
    date_count = 3

    def test_object_datetimes(self):
        d2011 = datetime.date(year=2011, month=1, day=1)
        self.assertEqual(len(Date.objects.language('en').datetimes("shared_date", "year")), 2)
        self.assertEqual(len(Date.objects.language('en').datetimes("shared_date", "month")), 3)
        self.assertEqual(len(Date.objects.language('en').datetimes("shared_date", "day")), 3)
        self.assertEqual(len(Date.objects.language('en').datetimes("shared_date", "day").filter(shared_date__gt=d2011)), 2)

