# -*- coding: utf-8 -*-
try:
    from urlparse import urlparse
    from urllib import unquote
except ImportError:
    from urllib.parse import urlparse, unquote
