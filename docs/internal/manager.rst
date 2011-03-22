###################
:mod:`nani.manager`
###################

.. data:: FALLBACK_LANGUAGES

.. class:: FieldTranslator(dict)

    .. method:: __init__(self, manager)
        
    .. method:: get(self, key)
    
    .. method:: build(self, key)


.. class:: ValuesMixin

    .. method:: _strip_master(self, key)

    .. method:: iterator(self)
        
.. class:: TranslationQueryset

    .. attribute:: override_classes
    
    .. method:: __init__(self, model=None, query=None, using=None, real=None)

    .. attribute:: translations_manager
    
    .. attribute:: shared_model
        
    .. attribute:: field_translator

    .. attribute:: shared_local_field_names
    
    .. method:: _translate_args_kwargs(self, *args, **kwargs)
    
    .. method:: _translate_fieldnames(self, fieldnames)

    .. method:: _recurse_q(self, q)
    
    .. method:: _find_language_code(self, q)
    
    .. method:: _split_kwargs(self, **kwargs)
    
    .. method:: _get_.. class::(self, klass)
    
    .. method:: _get_shared_query_set(self)
    
    .. method:: language(self, language_code=None)
        
    .. method:: create(self, **kwargs)
    
    .. method:: get(self, *args, **kwargs)

    .. method:: filter(self, *args, **kwargs)

    .. method:: aggregate(self, *args, **kwargs)

    .. method:: latest(self, field_name=None)

    .. method:: in_bulk(self, id_list)

    .. method:: delete(self)
    
    .. method:: delete_translations(self)
        
    .. method:: update(self, **kwargs)

    .. method:: values(self, *fields)

    .. method:: values_list(self, *fields, **kwargs)

    .. method:: dates(self, field_name, kind, order='ASC')

    .. method:: exclude(self, *args, **kwargs)

    .. method:: complex_filter(self, filter_obj)

    .. method:: annotate(self, *args, **kwargs)

    .. method:: order_by(self, *field_names)
    
    .. method:: reverse(self)

    .. method:: defer(self, *fields)

    .. method:: only(self, *fields)
    
    .. method:: _clone(self, klass=None, setup=False, **kwargs)
    
    .. method:: __getitem__(self, item)
    
    .. method:: iterator(self)


.. class:: TranslationManager

    .. method:: language(self, language_code=None)
    
    .. method:: untranslated(self)
    
    .. attribute:: translations_model
        
    .. method:: get_query_set(self)
    
    .. method:: contribute_to_class(self, model, name)
        
    .. method:: contribute_real_manager(self)
    
    .. method:: contribute_fallback_manager(self)


.. class:: FallbackQueryset

    .. method:: __init__(self, *args, **kwargs)
    
    .. method:: iterator(self)
    
    .. method:: use_fallbacks(self, *fallbacks)

    .. method:: _clone(self, klass=None, setup=False, **kwargs)


.. class:: TranslationFallbackManager

    .. method:: use_fallbacks(self, *fallbacks)

    .. method:: get_query_set(self)


.. class:: TranslationAwareQueryset

    .. method:: __init__(self, *args, **kwargs)
        
    .. method:: _translate_args_kwargs(self, *args, **kwargs)

    .. method:: _recurse_q(self, q)
    
    .. method:: _translate_fieldnames(self, fields)

    .. method:: language(self, language_code=None)
    
    .. method:: get(self, *args, **kwargs)

    .. method:: filter(self, *args, **kwargs)
    
    .. method:: aggregate(self, *args, **kwargs)

    .. method:: latest(self, field_name=None)

    .. method:: in_bulk(self, id_list)

    .. method:: values(self, *fields)

    .. method:: values_list(self, *fields, **kwargs)

    .. method:: dates(self, field_name, kind, order='ASC')

    .. method:: exclude(self, *args, **kwargs)

    .. method:: complex_filter(self, filter_obj)

    .. method:: annotate(self, *args, **kwargs)

    .. method:: order_by(self, *field_names)
    
    .. method:: reverse(self)

    .. method:: defer(self, *fields)

    .. method:: only(self, *fields)
    
    .. method:: _clone(self, klass=None, setup=False, **kwargs)
    
    .. method:: _filter_extra(self, extra_filters)
    

.. class:: TranslationAwareManager

    .. method:: get_query_set(self)
