##################
:mod:`nani.models`
##################


.. function:: create_translations_model(model, related_name, meta, **fields)


.. class:: TranslatedFields

    .. method:: __init__(self, meta=None, **fields)

    .. method:: contribute_to_.. class::(self, cls, name)


.. class:: BaseTranslationModel

    .. method:: __init__(self, *args, **kwargs)

    .. class:: Meta:
    
        .. attribute:: abstract
        

.. class:: TranslateableModelBase

    .. method:: __new__(cls, name, bases, attrs)
    

.. class:: TranslateableModel

    .. attribute:: __metaclass__
    
    .. attribute:: objects
    
    .. class:: Meta
    
        .. attribute:: abstract
    
    .. method:: __init__(self, *args, **kwargs)

    
    .. classmethod:: contribute_translations(cls, rel)

    .. classmethod:: save_translations(cls, instance, **kwargs)
    
    .. method:: translate(self, language_code)
    
    .. method:: safe_translation_getter(self, name, default=None)
    
    .. method:: get_available_languages(self)
    
    .. attribute:: _shared_field_names

    .. attribute:: _translated_field_names
