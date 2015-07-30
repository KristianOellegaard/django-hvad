# -*- coding: utf-8 -*-
from datetime import datetime
from collections import namedtuple

#===============================================================================

USER = [
    dict(username='admin', is_superuser=True),
    dict(username='staff', is_staff=True),
    dict(username='user'),
]

#===============================================================================

NormalData = namedtuple('NormalData', 'shared_field translated_field')

NORMAL = {
    1: NormalData(
        shared_field=u'Shared1',
        translated_field={'en': u'English1', 'ja': u'日本語一',},
    ),
    2: NormalData(
        shared_field=u'Shared2',
        translated_field={'en': u'English2', 'ja': u'日本語二',},
    ),
}

QONORMAL = NORMAL

#===============================================================================

StandardData = namedtuple('StandardData', 'normal_field normal')

STANDARD = {
    1: StandardData(normal_field=u'normal1', normal=1),
    2: StandardData(normal_field=u'normal2', normal=2),
    3: StandardData(normal_field=u'normal3', normal=1),
    4: StandardData(normal_field=u'normal4', normal=2),
}

#===============================================================================

ConcreteABData = namedtuple('ConcreteABData',
                            'shared_field_a shared_field_b shared_field_ab '
                            'translated_field_a translated_field_b translated_field_ab')

CONCRETEAB = {
    1: ConcreteABData(
        shared_field_a=u'SharedA1',
        shared_field_b=1,
        shared_field_ab=u'SharedAB1',
        translated_field_a={'en': 1, 'ja': 2,},
        translated_field_b={'en': u'EnglishB1', 'ja': u'日本語一',},
        translated_field_ab={'en': u'EnglishAB1', 'ja': u'日本語一',},
    ),
    2: ConcreteABData(
        shared_field_a=u'SharedA2',
        shared_field_b=2,
        shared_field_ab=u'SharedAB2',
        translated_field_a={'en': 2, 'ja': 1,},
        translated_field_b={'en': u'EnglishB2', 'ja': u'日本語二',},
        translated_field_ab={'en': u'EnglishAB2', 'ja': u'日本語二',},
    ),
}

#===============================================================================

DateData = namedtuple('DateData', 'shared_date translated_date')

DATE_VALUES = (
    # Values here must be in ascending order so earliest/latest tests work
    datetime(year=1988, month=7, day=4),
    datetime(year=2011, month=1, day=26),
    datetime(year=2011, month=2, day=16, hour=5, minute=1, second=14),
)

DATE = {
    # Be sure to update DATE_REVERSED when modifying this
    1: DateData(shared_date=DATE_VALUES[0],
                translated_date={'en': DATE_VALUES[2], 'ja': DATE_VALUES[1],},),
    2: DateData(shared_date=DATE_VALUES[2],
                translated_date={'en': DATE_VALUES[1], 'ja': DATE_VALUES[0],},),
    3: DateData(shared_date=DATE_VALUES[1],
                translated_date={'en': DATE_VALUES[0], 'ja': DATE_VALUES[2],},),
}

DATE_REVERSED = {
    DATE_VALUES[0]: DateData(shared_date=1, translated_date={'en': 3, 'ja': 2}),
    DATE_VALUES[1]: DateData(shared_date=3, translated_date={'en': 2, 'ja': 1}),
    DATE_VALUES[2]: DateData(shared_date=2, translated_date={'en': 1, 'ja': 3}),
}

#===============================================================================
