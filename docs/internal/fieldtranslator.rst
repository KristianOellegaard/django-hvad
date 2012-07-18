###########################
:mod:`hvad.fieldtranslator`
########################### 

.. module:: hvad.fieldtranslator

.. data:: TRANSLATIONS
    
    Constant to identify :term:`Shared Model` classes.
    
.. data:: TRANSLATED
    
    Constant to identify :term:`Translations Model` classes.
    
.. data:: NORMAL

    Constant to identify normal models.
    
.. data:: MODEL_INFO

    Caches the model informations in a dictionary with the model class as keys
    and the return value of :func:`_build_model_info` as values.

.. function:: _build_model_info(model)

    Builds the model information dictionary for a model. The dictionary holds
    three keys: ``'type'``, ``'shared'`` and ``'translated'``. ``'type'`` is one
    of the constants :data:`TRANSLATIONS`, :data:`TRANSLATED` or :data:`NORMAL`.
    ``'shared'`` and ``'translated'`` are a list of shared and translated
    fieldnames. This method is used by :func:`get_model_info`. 

.. function:: get_model_info(model)
    
    Returns the model information either from the :data:`MODEL_INFO` cache or by
    calling :func:`_build_model_info`.

.. function:: _get_model_from_field(starting_model, fieldname)

    Get the model the field ``fieldname`` on ``starting_model`` is pointing to.
    This function uses :meth:`get_field_by_name` on the starting model's options
    (meta) to figure out what type of field it is and what the target model is. 

.. function:: translate(querykey, starting_model)

    Translates a querykey (eg ``'myfield__someotherfield__contains'``) to be
    language aware by spanning the translations relations wherever necessary. It
    also figures out what extra filters to the :term:`Translations Model` tables
    are necessary. Returns the translated querykey and a list of language joins
    which should be used to further filter the queryset with the current
    language.