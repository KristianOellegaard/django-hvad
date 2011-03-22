###################
:mod:`nani.manager`
###################

.. module:: nani.manager

This module is where the mist of the functionality is implemented.

.. data:: FALLBACK_LANGUAGES

    The default sequence for fallback languages
    

.. class:: FieldTranslator(dict)

    .. method:: __init__(self, manager)
        
    .. method:: get(self, key)
    
    .. method:: build(self, key)


.. class:: ValuesMixin

    A mixin class for :class:`django.db.models.query.ValuesQuerySet` which
    implements the functionality needed by :meth:`TranslationQueryset.values`
    and :meth:`TranslationQueryset.values_list`.

    .. method:: _strip_master(self, key)
    
        Strips ``'master__'`` from the key if the key starts with that string.

    .. method:: iterator(self)
        
        Iterates over the rows from the superclass iterator and calls
        :meth:`_strip_master` on the key if the row is a dictionary.
        

.. class:: TranslationQueryset

    .. attribute:: override_classes
    
        A dictionary of django classes to nani classes to mixin when
        :meth:`_clone` is called with an explicit *klass* argument.
        
    .. attribute:: _local_field_names
    
        A list of field names on the :term:`Shared Model`.
        
    .. attribute:: _field_translator
    
        The cached field translator for this manager.
    
    .. attribute:: _real_manager
    
        The real manager of the :term:`Shared Model`.
        
    .. attribute:: _fallback_manager
    
        The fallback manager of the :term:`Shared Model`.
    
    .. attribute:: _language_code
    
        The language code of this queryset
    
    .. attribute:: translations_manager
    
        The (real) manager of the :term:`Translations Model`.
    
    .. attribute:: shared_model
    
        The :term:`Shared Model`.
        
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
