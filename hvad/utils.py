from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import get_language
from hvad.exceptions import WrongManager

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
    from hvad.manager import TranslationAwareManager
    manager = TranslationAwareManager()
    manager.model = model
    return manager

def get_translation_aware_custom_manager(model):
    """
    Creates a translation-aware manager for a given model. The new manager
    is built from model's default manager, with Manager or TranslationManager
    bases replaced with TranslationAwareManager. This allows the translation-aware
    manager to retain all custom functions.
    If the default manager has not been customized (therefore, is Manager or
    TranslationManager), a regular TranslationAwareManager is returned.

    Also, the new translation-aware manager uses a translation-aware queryset built
    on the model's default manager queryset_class setting. If not set, it will
    default to the regular TranslationAwareQueryset.

    Two calls with the same model will return the same class object, so introspection
    functions work as intended.

    NOTE: methods of the model's default manager and its queryset may not user super().
    """
    from django.db.models import Manager
    from hvad.manager import (TranslationManager, TranslationAwareManager,
                              TranslationQueryset, TranslationAwareQueryset)
    try:
        manager = model._translation_aware_default_manager
    except AttributeError:
        default_manager = model._default_manager.__class__
        if issubclass(TranslationManager, default_manager): # Not the other way around
            # Manager was not customized, use regular translation-aware manager
            manager_class = TranslationAwareManager
        else:
            # Manager was customized, build a translation-aware customized manager
            bases = [TranslationAwareManager if issubclass(TranslationManager, b) else b
                     for b in default_manager.__bases__]
            try:
                manager_class = type('TranslationAware' + default_manager.__name__,
                                    tuple(bases), {
                                        k:v for k,v in default_manager.__dict__.items()
                                        if k not in ('get_queryset', 'get_query_set')
                                    })
            except TypeError as e:
                if 'duplicate base class' in e.message:
                    raise WrongManager('The default manager of the model may not '
                                       'inherit both TranslationManager and Manager when '
                                       'using get_translation_aware_manager. '
                                       'Manager %r from model %r looks like it does.' %
                                       (default_manager.__name__, model._meta.object_name))
                raise

            try:
                qs_class = model._default_manager.translation_aware_queryset_class
            except AttributeError:
                queryset_class = getattr(model._default_manager, 'queryset_class',
                                         model._default_manager.get_queryset().__class__)
                qs_class = TranslationAwareQueryset._build_from_unaware(queryset_class)
                model._default_manager.translation_aware_queryset_class = qs_class
            manager_class.queryset_class = qs_class
        manager = manager_class()
        manager.model = model
        model._translation_aware_default_manager = manager
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
                                   "hvad.utils.get_translation_aware_manager." %
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
