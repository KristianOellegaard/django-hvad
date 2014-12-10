# -*- coding: utf-8 -*-
try:
    from django.utils.encoding import force_unicode
except ImportError: #pragma: no cover
    def force_unicode(s): # Django <1.4
        return str(s)
