# -*- coding: utf-8 -*-
try:
    from urllib import urlencode
    from urlparse import urlparse
    from urllib import unquote
except ImportError:
    from urllib.parse import urlencode, urlparse, unquote
