##################
:mod:`hvad.models`
##################

.. module:: hvad.models

.. data:: NoTranslation

    A special value used with :meth:`~hvad.models.TranslatableModel.__init__`
    to prevent automatic creation of a translation.

.. function:: prepare_translatable_model(sender)
    Gets called from :class:`~django.db.models.Model` after Django has
    completed its setup. It customizes model creation for translations.
    Most notably, it performs checks, overrides ``_meta`` methods and defines
    translation-aware manager on models that inherit
    :class:`~hvad.models.TranslatableModel`.

****************
TranslatedFields
****************

.. class:: TranslatedFields

    A wrapper for the translated fields which is set onto
    :class:`TranslatableModel` subclasses to define what fields are translated.

    .. method:: contribute_to_class(self, cls, name)
    
        Invoked by Django while setting up a model that defines translated fields.
        Django passes is the model being built as ``cls`` and the field name
        used for translated fields as ``name``.

        It triggers translations model creation from the list of field the
        ``TranslatedFields`` object was created with, and glues the shared
        model and the translations model together.

    .. method:: create_translations_model(self, model, related_name)

        A model factory used to create the :term:`Translations Model` for the
        given shared ``model``. The translations model will include:

        * A foreign key back to the shared model, named ``master``, with the
          given ``related_name``.
        * A ``language_code`` field, indexed together with ``master``, for
          looking up a shared model instance's translations.
        * All fields passed to ``TranslatedFields`` object.

        Adds the new model to the shared model's module and returns it.

    .. method:: contribute_translations(self, model, translations_model, related_name)

        Glues the shared ``model`` and the ``translations_model`` together.
        This step includes setting up attribute descriptors for all translatable
        fields onto the shared ``model``.

    .. method:: _scan_model_bases(self, model)

        Recursively walks all ``model``'s base classes, looking for translation
        models and collecting translatable fields. Used to build the inheritance
        tree of a :term:`Translations Model`.

        Returns the list of bases and the list of fields.

    .. method:: _build_meta_class(self, model, tfields)

        Creates the :djterm:`Meta <meta-options>` class for the
        :term:`Translations Model` passed as ``model``. Takes ``tfields`` as a
        list of all fields names referring to translatable fields.

        Returns the created meta class.

    .. staticmethod:: _split_together(constraints, fields, name)

        Helper method that partitions constraint tuples into shared-model
        constraints and translations model constraints. Argument ``constraints``
        is an iterable of contrain tuples, ``fields`` is the list of translated
        field names and ``name`` is the name of the option being handled (used
        for raising exceptions).

        Returns two list of constraints. First for shared model, second for
        translations model. Raises an
        :exc:`~django.core.exceptions.ImproperlyConfigured` exception if a
        constraint has both translated and untranslated fields.

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
