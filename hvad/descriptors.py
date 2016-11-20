from django.apps import registry
from django.utils.translation import get_language
from hvad.settings import hvad_settings
from hvad.utils import get_translation, set_cached_translation

__all__ = ()


class TranslatedAttribute(object):
    """ Proxy descriptor, forwarding attribute access to loaded translation.
        If no translation is loaded, it will attempt to load one depending on settings
    """

    def __init__(self, model, name):
        self.translations_model = model._meta.translations_model
        self.name = name
        self.tcache_name = model._meta.translations_cache
        self._NoTranslationError = type('NoTranslationError',
                                        (AttributeError, model._meta.translations_model.DoesNotExist),
                                        {})
        super(TranslatedAttribute, self).__init__()

    def load_translation(self, instance):
        if not hvad_settings.AUTOLOAD_TRANSLATIONS:
            raise AttributeError('Field %r is a translatable field, but no translation is loaded '
                                 'and auto-loading is disabled because '
                                 'settings.HVAD[\'AUTOLOAD_TRANSLATIONS\'] is False' % self.name)
        try:
            translation = get_translation(instance)
        except instance._meta.translations_model.DoesNotExist:
            raise self._NoTranslationError('Accessing a translated field requires that '
                                           'the instance has a translation loaded, or a '
                                           'valid translation in current language (%s) '
                                           'loadable from the database' % get_language())
        set_cached_translation(instance, translation)
        return translation

    def __get__(self, instance, instance_type=None):
        if not instance:
            if not registry.apps.ready: #pragma: no cover
                raise AttributeError('Attribute not available until registry is ready.')
            return self.translations_model._meta.get_field(self.name).default
        try:
            translation = getattr(instance, self.tcache_name)
        except AttributeError:
            translation = self.load_translation(instance)
        return getattr(translation, self.name)
    
    def __set__(self, instance, value):
        try:
            translation = getattr(instance, self.tcache_name)
        except AttributeError:
            translation = self.load_translation(instance)
        setattr(translation, self.name, value)
    
    def __delete__(self, instance):
        try:
            translation = getattr(instance, self.tcache_name)
        except AttributeError:
            translation = self.load_translation(instance)
        delattr(translation, self.name)


class LanguageCodeAttribute(TranslatedAttribute):
    """
    The language_code attribute is different from other attribtues as it cannot
    be deleted. Trying to do so will always cause an attribute error.
    
    """
    def __init__(self, model):
        super(LanguageCodeAttribute, self).__init__(model, 'language_code')
    
    def __set__(self, instance, value):
        raise AttributeError("The 'language_code' attribute cannot be changed directly.")
    
    def __delete__(self, instance):
        raise AttributeError("The 'language_code' attribute cannot be deleted.")
