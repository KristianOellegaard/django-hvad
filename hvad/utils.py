""" Miscellaneous standalone functions for manipulating translations.
    Mostly intended for internal use and third-party modules.
"""
import django
from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import get_language, get_language_info as original_get_language_info
from hvad.exceptions import WrongManager
from hvad.settings import hvad_settings

__all__ = (
    'translation_rater',
    'get_translation_aware_manager',
)

#=============================================================================
# Public utils

def translation_rater(*languages):
    """ Return a translation rater for the given set of languages.
        If language list is omitted, use:
            - current language, then
            - site's default language, then
            - site's fallback languages, then
            - equal score of -1 for all other languages
    """
    if not languages:
        languages = (get_language(), hvad_settings.DEFAULT_LANGUAGE) + hvad_settings.FALLBACK_LANGUAGES
    score_dict = dict((code, idx) for idx, code in enumerate(languages[::-1], 1))
    return lambda translation: score_dict.get(translation.language_code, -1)

def get_translation_aware_manager(model):
    """ Return a manager for an untranslatable model, that recognizes
        hvad translations.
    """
    if hasattr(model._meta, 'translations_model'):
        raise TypeError('get_translation_aware_manager must only be used on regular, '
                        'untranslatable model. Model %s is translatable.' % model.__name__)
    from hvad.manager import TranslationAwareManager
    manager = TranslationAwareManager()
    manager.model = model
    return manager

#=============================================================================
# Translation manipulators

def get_cached_translation(instance):
    """ Get currently cached translation of the instance.
        Intended for internal use and third-party modules.
        User code should use instance.translations.active instead.
    """
    return instance._meta.get_field('_hvad_query').get_cached_value(instance, None)

def set_cached_translation(instance, translation):
    """ Sets the translation cached onto instance.
        Intended for internal use and third-party modules.
        User code should use instance.translations.activate(translation) instead
        - Passing None unsets the translation cache
        - Returns the translation that was loaded before
    """
    hvad_query = instance._meta.get_field('_hvad_query')
    previous = hvad_query.get_cached_value(instance, None)
    if translation is None:
        if previous is not None:
            hvad_query.delete_cached_value(instance)
    else:
        hvad_query.set_cached_value(instance, translation)
    return previous

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

def get_language_info(lang_code):
    if lang_code == 'zh':
        lang_code = 'zh-hans'
    return original_get_language_info(lang_code)
