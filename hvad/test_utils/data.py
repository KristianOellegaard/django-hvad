# -*- coding: utf-8 -*-
from datetime import datetime
    
DOUBLE_NORMAL = {
    1: {
        'shared_field': u'Shared1',
        'translated_field_en': u'English1',
        'translated_field_ja': u'日本語一',
    },
    2: {
        'shared_field': u'Shared2',
        'translated_field_en': u'English2',
        'translated_field_ja': u'日本語二',
    },
}

D1 = datetime(year=1988, month=7, day=4)
D2 = datetime(year=2011, month=1, day=26)
D3 = datetime(year=2011, month=2, day=16, hour=5, minute=1, second=14)

DATES = {
    1: {
        'shared_date': D1, 
        'translated_date_en': D3,
        'translated_date_ja': D2,
    },
    2: {
        'shared_date': D3, 
        'translated_date_en': D2,
        'translated_date_ja': D1,
    },
    3: {
        'shared_date': D2, 
        'translated_date_en': D1,
        'translated_date_ja': D3,
    },
}

DATES_REVERSED = {}
for pk, data in DATES.items():
    for key, value in data.items():
        if value not in DATES_REVERSED:
            DATES_REVERSED[value] = {}
        DATES_REVERSED[value][key] = pk