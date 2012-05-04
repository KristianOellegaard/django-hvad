from hvad.test_utils.data import DATES_REVERSED, D3
from hvad.test_utils.fixtures import DatesMixin
from hvad.test_utils.testcase import NaniTestCase
from testproject.app.models import Date
import datetime

class LatestTests(NaniTestCase, DatesMixin):
    def test_shared_latest(self):
        latest = Date.objects.language('en').latest('shared_date')
        self.assertEqual(latest.pk, DATES_REVERSED[D3]['shared_date'])
        
    def test_translated_latest(self):
        latest = Date.objects.language('en').latest('translated_date')
        self.assertEqual(latest.pk, DATES_REVERSED[D3]['translated_date_en'])
        latest = Date.objects.language('ja').latest('translated_date')
        self.assertEqual(latest.pk, DATES_REVERSED[D3]['translated_date_ja'])

class DatesTests(NaniTestCase, DatesMixin):
    def test_objects_dates(self):
        d2011 = datetime.date(year=2011, month=1, day=1)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "year")), 2)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "month")), 3)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "day")), 3)
        self.assertEqual(len(Date.objects.language('en').dates("shared_date", "day").filter(shared_date__gt=d2011)), 2)