##################
:mod:`hvad.models`
##################

.. module:: hvad.models

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

    .. attribute:: objects
    
        An instance of :class:`hvad.manager.TranslationManager`.
    
    .. attribute:: _shared_field_names
    
        A list of field on the :term:`Shared Model`.

    .. attribute:: _translated_field_names
    
        A list of field on the :term:`Translations Model`.
    
    .. classmethod:: save_translations(cls, instance, **kwargs)
    
        This classmethod is connected to the model's post save signal from
        :func:`prepare_translatable_model` and saves the cached translation if it's
        available.
    
    .. method:: translate(self, language_code)
    
        Initializes a new instance of the :term:`Translations Model` (does not
        check the database if one for the language given already exists) and
        sets it as cached translation. Used by end users to translate instances
        of a model.
    
    .. method:: safe_translation_getter(self, name, default=None)
    
        Helper method to safely get a field from the :term:`Translations Model`.
        
    .. method:: lazy_translation_getter(self, name, default=None)

        Helper method to get the cached translation, and in the case the cache
        for some reason doesnt exist, it gets it from the database.
    
    .. method:: get_available_languages(self)
    
        Returns a list of language codes in which this instance is available.


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
