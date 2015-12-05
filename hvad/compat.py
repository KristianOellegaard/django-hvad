import sys
PYTHON_MAJOR, PYTHON_MINOR = sys.version_info[0:2]

__all__ = ('with_metaclass', 'MethodType', 'StringIO', 'string_types',
           'urlencode', 'urlparse', 'unquote')

#=============================================================================

def with_metaclass(meta, *bases):
    ''' Python 2/3 cross-compatible way to use a metclass
        Remove when support for Python 2 is dropped.
    '''
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})

#=============================================================================

if PYTHON_MAJOR == 2:
    from types import MethodType as OriginalMethodType
    def MethodType(function, instance):
        return OriginalMethodType(function, instance, instance.__class__)

    string_types = (str, unicode)
    from urllib import urlencode
    from urlparse import urlparse
    from urllib import unquote

    if PYTHON_MINOR >= 6:
        from io import StringIO
    else: #pragma: no cover
        from StringIO import StringIO

else:
    from types import MethodType
    string_types = (str,)
    from urllib.parse import urlencode, urlparse, unquote
    from io import StringIO

