##################
:mod:`hvad.models`
##################

.. module:: hvad.models

.. data:: NoTranslation

    A special value used with :meth:`~hvad.models.TranslatableModel.__init__`
    to prevent automatic creation of a translation.

.. function:: create_translations_model(model, related_name, meta, **fields)

    A model factory used to create the :term:`Translations Model`. Makes sure
    that the *unique_together* option on the options (meta) contain
    ``('language_code', 'master')`` as they always have to be unique together.
    Sets the ``master`` foreign key to *model* onto the
    :term:`Translations Model` as well as the ``language_code`` field, which is
    a database indexed char field with a maximum of 15 characters.
    
    Returns the new model. 

.. function:: contribute_translations(cls, rel)

    Gets called from :func:`prepare_translatable_model` to set the
    descriptors of the fields on the :term:`Translations Model` onto the
    model.

.. function:: prepare_translatable_model(sender)

    Gets called from :class:`~django.db.models.Model`'s metaclass to
    customize model creation. Performs checks, then contributes translations
    and translation manager onto models that inherit
    :class:`~hvad.models.TranslatableModel`.

****************
TranslatedFields
****************

.. class:: TranslatedFields

    A wrapper for the translated fields which is set onto
    :class:`TranslatableModel` subclasses to define what fields are translated.
    
    Internally this is just used because Django calls the
    :meth:`contribute_to_class` method on all attributes of a model, if such a
    method is available.

    .. method:: contribute_to_class(self, cls, name)
    
        Calls :func:`create_translations_model`.


********************
BaseTranslationModel
********************

.. class:: BaseTranslationModel

    A baseclass for the models created by :func:`create_translations_model` to
    distinguish :term:`Translations Model` classes from other models. This model
    class is abstract.


******************
TranslatableModel        
******************

.. class:: TranslatableModel

    A model which has translated fields on it. Must define one and exactly one
    attribute which is an instance of :class:`TranslatedFields`. This model is
    abstract.
    
    If initalized with data, it splits the shared and translated fields and
    prepopulates both the :term:`Shared Model` and the
    :term:`Translations Model`. If no *language_code* is given,
    :func:`~django.utils.translation.get_language` is used to get the language
    for the :term:`Translations Model` instance that gets initialized.
    
    .. note:: When initializing a :class:`TranslatableModel`, positional
              arguments are only supported for the shared fields.

    .. method:: __init__(self, *args, **kwargs)

        Initializes the instance. Keyword arguments are split into translated
        and untranslated fields. Untranslated fields are passed to
        :class:`superclass <django.db.models.Model>`,
        while translated fields are passed to a newly-initializeded
        :term:`Translations Model` instance.

        Passing special value :data:`~hvad.models.NoTranslation` as ``language_code``
        skips initialization of the translation instance, leaving no translation
        loaded in the cache. Mainly useful to prevent double initialization
        in :meth:`~hvad.models.TranslatableModel.from_db`.

    .. method:: from_db(cls, db, field_names, values)

        Initializes a model instance from database-read field values. Overriden
        so it can pass ``NoTranslation`` to
        :meth:`~hvad.models.TranslatableModel.__init__`, avoiding double initialization
        of the :term:`Translations Model` instance.

    .. method:: save(self, *args, **kwargs)

        Saves the mode instance into the database. If ``update_fields`` is given,
        specified fields are split into translatable and untranslatable fields
        and passed to the appropriate ``save`` methods. In case ``update_fields``
        is specified and has only translatable or only untranslatable fields,
        only the :term:`Translations Model` or :term:`Shared Model` is saved.

        Saving is done in a transaction.

    .. method:: translate(self, language_code)
    
        Initializes a new instance of the :term:`Translations Model`.
        Inconditionnaly creates the new translation, without checking whether
        it exists in the database or in the translations cache. Sets the new
        translation as cached translation. Used by end users to translate instances
        of a model.

    .. method:: clean_fields(self, exclude=None)

        Validate the content of model fields. Overrides
        :meth:`superclass's clean_fields <django.db.models.Model.clean_fields>` to
        propagate the call to the :term:`Translations Model` as well, if one is
        currently cached.

    .. method:: validate_unique(self, exclude=None)

        Validate values of model fields marked as unique. Overrides
        :meth:`superclass's clean_fields <django.db.models.Model.validate_unique>` to
        propagate the call to the :term:`Translations Model` as well, if one is
        currently cached.

    .. attribute:: objects

        An instance of :class:`hvad.manager.TranslationManager`.

    .. method:: check(cls, **kwargs)

        Extend model checks to add hvad-specific checks, namely:

            * That translatable and untranslatable fields have different names.
            * That the default manager is translation-aware.

Extra information on _meta of Shared Models
===========================================

The options (meta) on :class:`TranslatableModel` subclasses have a few extra
attributes holding information about the translations.


translations_accessor
---------------------

The name of the attribute that holds the :class:`TranslatedFields` instance.


translations_model
------------------

The model class that holds the translations (:term:`Translations Model`).


translations_cache
------------------

The name of the cache attribute on this model.


Extra information on _meta of Translations Models
=================================================

The options (meta) on :class:`BaseTranslationModel` subclasses have a few extra
attributes holding information about the translations.


shared_model
------------

The model class that holds the shared fields (:term:`Shared Model`).
