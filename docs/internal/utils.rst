#################
:mod:`hvad.utils`
#################

.. module:: hvad.utils

.. function:: get_cached_translation(instance)

    Returns the cached translation from an instance or ``None``.
    Encapsulates a :func:`getattr` using the model's **translations_cache**.

.. function:: set_cached_translation(instance, translation)

    Sets the currently cached translation for the instance, and returns the
    translation that was loaded before the call. Passing ``None`` as translation
    will unload current translation and let the instance untranslated.

.. function:: combine(trans, klass)

    Combines a :term:`Shared Model` with a :term:`Translations Model` by taking
    the :term:`Translations Model` and setting it onto the
    :term:`Shared Model`'s translations cache.

    **klass** is the :term:`Shared Model` class. This argument is required as there
    is no way to distinguish a translation of a proxy model from that of a concrete
    model otherwise.

    This function is only intended for loading models from the database. For other
    uses, :func:`set_cached_translation` should be used instead.

.. function:: get_translation(instance, language_code=None)

    Returns the translation for an instance, in the specified language. If given
    language is None, uses :func:`~django.utils.translation.get_language` to get
    current language.

    Encapsulates a :func:`getattr` using the model's **translations_accessor** and
    a call to its :meth:`~django.db.models.query.QuerySet.get` method using the
    instance's primary key and given language_code as filters.

.. function:: load_translation(instance, language, enforce=False)

    Returns the translation for an instance.

    * If ``enforce`` is false, then ``language`` is used as a default language,
      if the ``instance`` has no language currently loaded.
    * If ``enforce`` is true, then ``language`` will be enforced upon the
      translation, ignoring cached translation if it is not in the given
      language.

    A valid translation instance is always returned. It will be loaded from the
    database as required. If this fails, a new, empty, ready-to-use translation
    will be returned.

    The instance itself is untouched.

.. function:: get_translation_aware_manager(model)

    Returns a manager for a normal model that is aware of translations and can
    filter over translated fields on translated models related to this normal
    model. 

.. class:: SmartGetFieldByName

    Smart version of the standard :meth:`get_field_by_name` on the options
    (meta) of Django models that raises a more useful exception when one tries
    to access translated fields with the wrong manager.

    .. method:: __init__(self, real)
    
    .. method:: __call__(self, meta, name)

.. function:: permissive_field_by_name(self, name)
    
    Returns the field from the :term:`Shared Model` or
    :term:`Translations Model`, if it is on either.
