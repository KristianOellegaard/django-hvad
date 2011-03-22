##################
:mod:`nani.models`
##################

.. module:: nani.models

.. function:: create_translations_model(model, related_name, meta, **fields)

    A model factory used to create the :term:`Translations Model`. Makes sure
    that the *unique_together* option on the options (meta) contain
    ``('language_code', 'master')`` as they always have to be unique together.
    Sets the ``master`` foreign key to *model* onto the
    :term:`Translations Model` as well as the ``language_code`` field, which is
    a database indexed char field with a maximum of 15 characters.
    
    Returns the new model. 


****************
TranslatedFields
****************

.. class:: TranslatedFields

    A wrapper for the translated fields which is set onto
    :class:`TranslateableModel` subclasses to define what fields are translated.
    
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


**********************
TranslateableModelBase        
**********************

.. class:: TranslateableModelBase

    Metaclass of :class:`TranslateableModel`.

    .. method:: __new__(cls, name, bases, attrs)


******************
TranslateableModel        
******************

.. class:: TranslateableModel

    A model which has translated fields on it. Must define one and exactly one
    attribute which is an instance of :class:`TranslatedFields`. This model is
    abstract.

    .. attribute:: objects
    
        An instance of :class:`nani.manager.TranslationManager`.
    
    .. attribute:: _shared_field_names
    
        A list of field on the :term:`Shared Model`.

    .. attribute:: _translated_field_names
    
        A list of field on the :term:`Translations Model`.
    
    .. classmethod:: contribute_translations(cls, rel)

    .. classmethod:: save_translations(cls, instance, **kwargs)
    
    .. method:: translate(self, language_code)
    
    .. method:: safe_translation_getter(self, name, default=None)
    
    .. method:: get_available_languages(self)
