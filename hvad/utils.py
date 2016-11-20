import django
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import get_language
from hvad.exceptions import WrongManager

__all__ = (
    'get_translation_aware_manager',
)

#=============================================================================
# Translation manipulators

def get_cached_translation(instance):
    'Get currently cached translation of the instance'
    return getattr(instance, instance._meta.translations_cache, None)

def set_cached_translation(instance, translation):
    '''Sets the translation cached onto instance.
        - Passing None unsets the translation cache
        - Returns the translation that was loaded before
    '''
    tcache = instance._meta.translations_cache
    previous = getattr(instance, tcache, None)
    if translation is None:
        if previous is not None:
            delattr(instance, tcache)
    else:
        setattr(instance, tcache, translation)
    return previous

def combine(trans, klass):
    """
    'Combine' the shared and translated instances by setting the translation
    on the 'translations_cache' attribute of the shared instance and returning
    the shared instance.

    The result is casted to klass (needed for proxy models).
    """
    combined = trans.master
    if klass._meta.proxy:
        combined.__class__ = klass
    setattr(combined, combined._meta.translations_cache, trans)
    return combined


def get_translation(instance, language_code=None):
    ''' Get translation by language. Fresh copy is loaded from DB.
        Can leverage prefetched data, like in .prefetch_related('translations')
    '''
    accessor = getattr(instance, instance._meta.translations_accessor)

    language_code = language_code or get_language()
    qs = accessor.all()
    if qs._result_cache is not None:
        # Take advantage of translation cache
        for obj in qs:
            if obj.language_code == language_code:
                return obj
        raise accessor.model.DoesNotExist('%r is not translated in %r' % (instance, language_code))
    return accessor.get(language_code=language_code)

def load_translation(instance, language, enforce=False):
    ''' Get or create a translation.
        Depending on enforce argument, the language will serve as a default
        or will be enforced by reloading a mismatching translation.

        If instance's active translation is in given language, this is
        a guaranteed no-op: it will be returned as is.
    '''
    trans_model = instance._meta.translations_model
    translation = get_cached_translation(instance)

    if translation is None or (enforce and translation.language_code != language):
        if instance.pk is None:
            translation = trans_model(language_code=language)
        else:
            try:
                translation = get_translation(instance, language)
            except trans_model.DoesNotExist:
                translation = trans_model(language_code=language)
    return translation

#=============================================================================

def get_translation_aware_manager(model):
    from hvad.manager import TranslationAwareManager
    manager = TranslationAwareManager()
    manager.model = model
    return manager

# remove when we drop support for django 1.8
class SmartGetFieldByName(object):
    """
    Get field by name from a shared model or raise a smart exception to help the
    developer.
    """
    def __init__(self, real):
        self.real = real
    
    def __call__(self, meta, name):
        assert not isinstance(self.real, SmartGetFieldByName)
        try:
            return self.real(name)
        except FieldDoesNotExist as e:
            try:
                meta.translations_model._meta.get_field_by_name(name)
            except FieldDoesNotExist:
                raise e
            else:
                raise WrongManager(meta, name)


class SmartGetField(object):
    ''' Smart get_field that raises a helpful exception on get_field() '''
    def __init__(self, real):
        assert not isinstance(real, SmartGetField)
        self.real = real

    def __call__(self, meta, name, *args, **kwargs):
        try:
            return self.real(name, *args, **kwargs)
        except FieldDoesNotExist as e:
            try:
                meta.translations_model._meta.get_field(name, *args, **kwargs)
            except FieldDoesNotExist:
                raise e
            else:
                raise WrongManager(meta, name)

#=============================================================================
# Internal sugar

class _MinimumDjangoVersionDescriptor(object): #pragma: no cover
    ''' Ensures methods that do not exist on current Django version raise a
        helpful message and an actual AttributeError
    '''
    def __init__(self, name, version):
        self.name = name
        self.version = version

    def __get__(self, obj, type=None):
        raise AttributeError('Method %s requires Django %s or newer' %
                             (self.name, '.'.join(str(x) for x in self.version)))

def minimumDjangoVersion(*args): #pragma: no cover
    ''' Method/attribute decorator making it unavailable on older Django versions
        e.g.: @minimumDjangoVersion(1, 4, 2)
    '''
    if django.VERSION >= args:
        return lambda x: x
    return lambda x: _MinimumDjangoVersionDescriptor(x.__name__, args)
