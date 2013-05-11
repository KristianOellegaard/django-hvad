# -*- coding: utf-8 -*-
import sys
from types import MethodType as OriginalMethodType

if sys.version_info.major == 2:
    def MethodType(function, instance):
        return OriginalMethodType(function, instance, instance.__class__)
else:
    MethodType = OriginalMethodType
