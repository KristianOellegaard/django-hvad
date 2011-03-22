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

    Any method on this queryset that returns a model instance or a queryset of
    model instances actually returns a :term:`Translations Model` which gets
    combined to behave like a :term:`Shared Model`. While this manager is on
    the :term:`Shared Model`, it is actually a manager for the
    :term:`Translations Model` since the model gets switched when this queryset
    is instantiated from the :class:`TranslationManager`.

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
    
        The language code of this queryset.
    
    .. attribute:: translations_manager
    
        The (real) manager of the :term:`Translations Model`.
    
    .. attribute:: shared_model
    
        The :term:`Shared Model`.
        
    .. attribute:: field_translator
    
        The field translator for this manager, sets :attr:`_field_translator` if
        it's ``None``.

    .. attribute:: shared_local_field_names
    
        Returns a list of field names on the :term:`Shared Model`, sets
        :attr:`_local_field_names` if it's ``None``.
    
    .. method:: _translate_args_kwargs(self, *args, **kwargs)
    
        Translates args (:class:`django.db.models.expressions.Q` objects) and
        kwargs (dictionary of query lookups and values) to be language aware, by
        prefixing fields on the :term:`Shared Model` with ``'master__'``. Uses
        :attr:`field_translator` for the kwargs and :meth:`_recurse_q` for the
        args. Returns a tuple of translated args and translated kwargs.
    
    .. method:: _translate_fieldnames(self, fieldnames)
    
        Translate a list of fieldnames by prefixing fields on the
        :term:`Shared Model` with ``'master__'`` using :attr:`field_translator`.
        Returns a list of translated fieldnames.

    .. method:: _recurse_q(self, q)
    
        Recursively walks a :class:`django.db.models.expressions.Q` object and
        translates it's query lookups to be prefixed by ``'master__'`` if they
        access a field on :term:`Shared Model`.
        
        Every :class:`django.db.models.expressions.Q` object has an attribute
        :attr:`django.db.models.expressions.Q.children` which is either a list
        of other :class:`django.db.models.expressions.Q` objects or a tuple
        where the key is the query lookup.
        
        This method returns a new :class:`django.db.models.expressions.Q`
        object.
    
    .. method:: _find_language_code(self, q)
    
        Searches a :class:`django.db.models.expressions.Q` object for
        language code lookups. If it finds a child
        :class:`django.db.models.expressions.Q` object that defines a language
        code, it returns that language code if it's not ``None``. Used in
        :meth:`get` to ensure a language code is defined.
        
        For more information about :class:`django.db.models.expressions.Q`
        objects, see :meth:`_recurse_q`.
        
        Returns the language code if one was found or ``None``.
    
    .. method:: _split_kwargs(self, **kwargs)
    
        Splits keyword arguments into two dictionaries holding the shared and
        translated fields.
        
        Returns a tuple of dictionaries of shared and translated fields.
    
    .. method:: _get_class(self, klass)
    
        Given a :class:`django.db.models.query.QuerySet` class or subclass, it
        checks if the class is a subclass of any class in
        :attr:`override_classes` and if so, returns a new class which mixes
        the initial class, the class from :attr:`override_classes` and
        :class:`TranslationQueryset`. Otherwise returns the class given.
    
    .. method:: _get_shared_query_set(self)
    
        Returns a clone of this queryset but for the shared model. Does so by
        using :attr:`_real_manager` and filtering over this queryset. Returns a
        queryset for the :term:`Shared Model`.
    
    .. method:: language(self, language_code=None)
    
        Specifies a language for this queryset. This sets the
        :attr:`_language_code` and filters by the language code.
        
        If no language code is given,
        :func:`django.utils.translations.get_language` is called to get the
        current language.
        
        Returns a queryset.
        
    .. method:: create(self, **kwargs)
    
        Creates a new instance using the kwargs given. If :attr:`_language_code`
        is not set and language_code is not in kwargs, it uses
        :func:`django.utils.translations.get_language` to get the current
        language and injects that into kwargs.
        
        This causes two queries as opposed to the one by the normal queryset.
        
        Returns the newly created (combined) instance.
    
    .. method:: get(self, *args, **kwargs)
    
        Gets a single instance from this queryset using the args and kwargs
        given. The args and kwargs are translated using
        :meth:`_translate_args_kwargs`.
        
        If a language code is given in the kwargs, it calls :meth:`language`
        using the language code provided. If none is given in kwargs, it uses
        :meth:`_find_language_code` on the
        :class:`django.db.models.expressions.Q` objects given in args. If no
        args were given or they don't contain a language code, it searches the
        :class:`django.db.models.sql.where.WhereNode` objects on the current
        queryset for language codes. If none was found, it calls
        :meth:`language` without an argument, which in turn uses 
        :func:`django.utils.translations.get_language` to enforce a language to
        be used in this queryset.
        
        Returns a (combined) instance if one can be found for the filters given,
        otherwise raises an appropriate exception depending on whether no or
        multiple objects were found.

    .. method:: filter(self, *args, **kwargs)
        
        Translates args and kwargs using :meth:`_translate_args_kwargs` and
        calls the superclass using the new args and kwargs.

    .. method:: aggregate(self, *args, **kwargs)
    
        Not implemented yet.

    .. method:: latest(self, field_name=None)
    
        Translates the fieldname (if given) using :attr:`field_translator` and
        calls the superclass.

    .. method:: in_bulk(self, id_list)
    
        Not implemented yet.

    .. method:: delete(self)
    
        Deletes the :term:`Shared Model` using :meth:`_get_shared_query_set`.
    
    .. method:: delete_translations(self)
    
        Deletes the translations (and **only** the translations) by first
        breaking their relation to the :term:`Shared Model` and then calling the
        delete method on the superclass. This uses two queries.
        
    .. method:: update(self, **kwargs)
    
        Updates this queryset using kwargs. Calls :meth:`_split_kwargs` to get
        two dictionaries holding only the shared or translated fields
        respectively. If translated fields are given, calls the superclass with
        the translated fields. If shared fields are given, uses
        :meth:`_get_shared_query_set` to update the shared fields.
        
        If both shared and translated fields are updated, two queries are
        executed, if only one of the two are given, one query is executed.
        
        Returns the count of updated objects, which if both translated and
        shared fields are given is the sum of the two update calls. 

    .. method:: values(self, *fields)
    
        Translates fields using :meth:`_translated_fieldnames` and calls the
        superclass.

    .. method:: values_list(self, *fields, **kwargs)
    
        Translates fields using :meth:`_translated_fieldnames` and calls the
        superclass.

    .. method:: dates(self, field_name, kind, order='ASC')
    
        Not implemented yet.

    .. method:: exclude(self, *args, **kwargs)
    
        Not implemented yet.

    .. method:: complex_filter(self, filter_obj)
    
        Not really implemented yet, but if filter_obj is an empty dictionary it
        just returns this queryset, since this is required to get admin to work.

    .. method:: annotate(self, *args, **kwargs)
    
        Not implemented yet.

    .. method:: order_by(self, *field_names)
    
        Translates fields using :meth:`_translated_fieldnames` and calls the
        superclass.
    
    .. method:: reverse(self)
    
        Not implemented yet.

    .. method:: defer(self, *fields)
    
        Not implemented yet.

    .. method:: only(self, *fields)
    
        Not implemented yet.
    
    .. method:: _clone(self, klass=None, setup=False, **kwargs)
    
        Injects *_local_field_names*, *_field_translator*, *_language_code*,
        *_real_manager* and *_fallback_manager* into *kwargs*. If a *klass* is
        given, calls :meth:`_get_class` to get a mixed class if necessary.
        
        Calls the superclass with the new *kwargs* and *klass*.
    
    .. method:: iterator(self)
    
        Iterates using the iterator from the superclass, if the objects yielded
        have a master, it yields a combined instance, otherwise the instance
        itself to enable non-cascading deletion.
        
        Interestingly, implementing the combination here also works for
        :meth:`get` and :meth:`__getitem__`.


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
