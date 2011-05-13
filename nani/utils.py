from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import get_language
from nani.exceptions import WrongManager
from django.db.models.loading import get_models
from django.db.models.fields.related import RelatedObject

def combine(trans):
    """
    'Combine' the shared and translated instances by setting the translation
    on the 'translations_cache' attribute of the shared instance and returning
    the shared instance.
    """
    combined = trans.master
    opts = combined._meta
    setattr(combined, opts.translations_cache, trans)
    return combined

def get_cached_translation(instance):
    return getattr(instance, instance._meta.translations_cache, None)

def get_translation(instance, language_code=None):
    opts = instance._meta
    if not language_code:
        language_code = get_language()
    accessor = getattr(instance, opts.translations_accessor)
    return accessor.get(language_code=language_code)

def get_translation_aware_manager(model):
    from nani.manager import TranslationAwareManager
    manager = TranslationAwareManager()
    manager.model = model
    return manager

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
        except FieldDoesNotExist:
            if name in meta.translations_model._meta.get_all_field_names():
                raise WrongManager("To access translated fields like %r from "
                                   "an untranslated model, you must use a "
                                   "translation aware manager, you can get one "
                                   "using "
                                   "nani.utils.get_translation_aware_manager." %
                                   name)
            raise
