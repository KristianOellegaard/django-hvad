from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import get_language
from nani.exceptions import WrongManager

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

def smart_get_field_by_name(self, name):
    try:
        return self._get_field_by_name(name)
    except FieldDoesNotExist:
        if name in self.translations_model._meta.get_all_field_names():
            raise WrongManager("To access translated fields like %r from an "
                               "untranslated model, you must use a translation "
                               "aware manager, you can get one using"
                               "nani.utils.get_translation_aware_manager.")
        raise