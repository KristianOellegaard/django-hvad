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


def collect_context_modifiers(instance, include=None, exclude=None, extra_kwargs=None):
    """
    helper method that updates the context with any instance methods that start
    with `context_modifier_`. `include` is an optional list of method names
    that also should be called. Any method names in `exclude` will not be
    added to the context.

    This helper is most useful when called from get_context_data()::

        def get_context_data(self, **kwargs):
            context = super(MyViewClass, self).get_context_data(**kwargs)
            context.update(collect_context_modifiers(self, extra_kwargs=kwargs))
            return context
    """
    include = include or []
    exclude = exclude or []
    extra_kwargs = extra_kwargs or {}
    context = {}

    for thing in dir(instance):
        if (thing.startswith('context_modifier_') or thing in include) and \
            not thing in exclude:
            context.update(getattr(instance, thing, lambda x:x)(**extra_kwargs))
    return context