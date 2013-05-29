# -*- coding: utf-8 -*-
try:
    from django.utils.encoding import force_unicode
except ImportError:
    def force_unicode(s):
        return str(s)
