###################
:mod:`hvad.manager`
###################

.. module:: hvad.manager

This module is where most of the functionality is implemented.

.. data:: FALLBACK_LANGUAGES

    The default sequence for fallback languages, populates itself from
    ``settings.LANGUAGES``, could possibly become a setting on it's own at some
    point.


***************
FieldTranslator
***************

.. class:: FieldTranslator

    The cache mentioned in this class is the instance of the class itself, since
    it inherits dict.
    
    Possibly this class is not feature complete since it does not care about
    multi-relation queries. It should probably use
    :func:`hvad.fieldtranslator.translate` after the first level if it hits
    the :term:`Shared Model`.てz
        
    .. method:: get(self, key)
    
        Returns the translated fieldname for *key*. If it's already cached,
        return it from the cache, otherwise call :meth:`build`
    
    .. method:: build(self, key)
    
        Returns the key prefixed by ``'master__'`` if it's a shared field,
        otherwise returns the key unchanged.


***********
ValuesMixin
***********

.. class:: ValuesMixin

    A mixin class for :class:`~django.db.models.query.ValuesQuerySet` which
    implements the functionality needed by :meth:`TranslationQueryset.values`
    and :meth:`TranslationQueryset.values_list`.

    .. method:: _strip_master(self, key)
    
        Strips ``'master__'`` from the key if the key starts with that string.

    .. method:: iterator(self)
        
        Iterates over the rows from the superclass iterator and calls
        :meth:`_strip_master` on the key if the row is a dictionary.


*********************
SkipMasterSelectMixin
*********************

.. class:: SkipMasterSelectMixin

    A mixin class for specialized querysets such as
    :class:`~django.db.models.query.DateQuerySet` and
    :class:`~django.db.models.query.DateTimeQuerySet` which forces
    :class:`~hvad.manager.TranslationQueryset` not to add the related lookup
    on the `master` field. This is required as those specialized querysets
    use DISTINCT, and added the related lookup brings along all fields on the
    :term:`Shared Model`, breaking the lookup.


*******************
TranslationQueryset
*******************

.. class:: TranslationQueryset

    Any method on this queryset that returns a model instance or a queryset of
    model instances actually returns a :term:`Translations Model` which gets
    combined to behave like a :term:`Shared Model`. While this manager is on
    the :term:`Shared Model`, it is actually a manager for the
    :term:`Translations Model` since the model gets switched when this queryset
    is instantiated from the :class:`TranslationManager`.

    .. attribute:: override_classes
    
        A dictionary of django classes to hvad classes to mixin when
        :meth:`_clone` is called with an explicit *klass* argument.
        
    .. attribute:: _local_field_names
    
        A list of field names on the :term:`Shared Model`.
        
    .. attribute:: _field_translator
    
        The cached field translator for this manager.
    
    .. attribute:: _language_code
    
        The language code of this queryset, or one of the following special values:

        - ``None``: :func:`~django.utils.translation.get_language`
          will be called to get the current language.
        - ``'all'``: no language filtering will be applied, a copy of an instance
          will be returned for every translation that matched the query.

    .. attribute:: _language_fallbacks

        A tuple of fallbacks used for this queryset, if fallbacks have been
        activated by :meth:`fallbacks`, or `None` otherwise.

        A ``None`` value in the tuple will be replaced with current language
        at query evaluation.

    .. attribute:: _hvad_switch_fields

        A tuple of attributes to move from the :term:`Translations Model` to the
        :term:`Shared Model` instance before returning objects to the caller. It
        is mostly used by :meth:`~django.db.models.query.QuerySet.extra` so
        additional values collected by the ``select`` argument are available on
        the final instance.

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
    
        Translates args (:class:`~django.db.models.Q` objects) and
        kwargs (dictionary of query lookups and values) to be language aware, by
        prefixing fields on the :term:`Shared Model` with ``'master__'``. Uses
        :attr:`field_translator` for the kwargs and :meth:`_recurse_q` for the
        args. Returns a tuple of translated args and translated kwargs.
    
    .. method:: _translate_fieldnames(self, fieldnames)
    
        Translate a list of fieldnames by prefixing fields on the
        :term:`Shared Model` with ``'master__'`` using :attr:`field_translator`.
        Returns a list of translated fieldnames.

    .. method:: _recurse_q(self, q)
    
        Recursively walks a :class:`~django.db.models.Q` object and
        translates it's query lookups to be prefixed by ``'master__'`` if they
        access a field on :term:`Shared Model`.
        
        Every :class:`~django.db.models.Q` object has an attribute
        :attr:`~django.db.models.Q.children` which is either a list
        of other :class:`~django.db.models.Q` objects or a tuple
        where the key is the query lookup.
        
        This method returns a new :class:`~django.db.models.Q`
        object.
    
    .. method:: _find_language_code(self, q)
    
        Searches a :class:`~django.db.models.Q` object for
        language code lookups. If it finds a child
        :class:`~django.db.models.Q` object that defines a language
        code, it returns that language code if it's not ``None``. Used in
        :meth:`get` to ensure a language code is defined.
        
        For more information about :class:`~django.db.models.Q`
        objects, see :meth:`_recurse_q`.
        
        Returns the language code if one was found or ``None``.
    
    .. method:: _split_kwargs(self, **kwargs)
    
        Splits keyword arguments into two dictionaries holding the shared and
        translated fields.
        
        Returns a tuple of dictionaries of shared and translated fields.
    
    .. method:: _get_class(self, klass)
    
        Given a :class:`~django.db.models.query.QuerySet` class or subclass, it
        checks if the class is a subclass of any class in
        :attr:`override_classes` and if so, returns a new class which mixes
        the initial class, the class from :attr:`override_classes` and
        :class:`TranslationQueryset`. Otherwise returns the class given.
    
    .. method:: _get_shared_queryset(self)
    
        Returns a clone of this queryset but for the shared model. Does so by
        creating a :class:`~django.db.models.query.QuerySet` on :attr:`shared_model`
        and filtering over this queryset. Returns a queryset for the :term:`Shared Model`.
    
    .. method:: _add_language_filter(self)

        Apply the language filter to current query. Language is retrieved from
        :attr:`_language_code`, or :func:`~django.utils.translation.get_language` if
        None. If :meth:`fallbacks` have been set, apply the additional join as well.

        Special value ``'all'`` will prevent any language filter from being applied,
        resulting in the query considering all translations, possibly returning
        the same instance mutiple times if several of its translations match.
        In that case, each instance will be :func:`combined <hvad.utils.combine>`
        with one of the matching translations.

        Applied filters include the base language filter on the language_code
        field, as well as any related model translation set up by
        :meth:`select_related`.

    .. method:: _add_select_related(self, language_code)

        .. versionadded:: 0.5

        Applies the related selections to current query. This includes the basic
        selection of ``master``, any relation specified through :meth:`select_related`
        and the translations of any translatable models it navigates through.

    .. method:: language(self, language_code=None)
    
        Specifies a language for this queryset. This sets the
        :attr:`_language_code`, but no filter are actually applied until
        :meth:`_add_language_filter` is called. This allows for query-time
        resolution of the None value. It is an error to call :meth:`language`
        multiple times on the same queryset.

        The following special values are accepted:

        - ``None``, or no value: :func:`~django.utils.translation.get_language`
          will be called to get the current language.
        - ``'all'``: no language filtering will be applied, a copy of an instance
          will be returned for every translation that matched the query, each
          copy being :func:`combined <hvad.utils.combine>` with one of the
          matching translations.

        Returns a queryset.

        .. note:: Support for using ``language('all')`` and :meth:`select_related`
                  on the same queryset is experimental. Please check the generated
                  queries and open an issue if you have any problem. Feedback
                  is appreciated as well.

    .. method:: fallbacks(self, *languages)

        .. versionadded:: 0.6

        Activates fallbacks for this queryset. This sets the
        :attr:`_language_fallbacks` attribute, but does not apply any join
        or filtering until :meth:`_add_language_filter` is called. This allows
        for query-time resolution of the ``None`` values in the list.

        The following special cases are accepted:

        - ``None`` as a single argument will disable fallbacks on the queryset.
        - An empty argument list will use :setting:`LANGUAGES` setting as a
          fallback list.
        - A ``None`` value a language will be replaced by the current language
          at query evalution time, by calling
          :func:`~django.utils.translation.get_language`

        Returns a queryset.

        .. note:: Using ``fallbacks`` and :meth:`select_related` on the
                  same queryset is not supported and will raise a
                  :exc:`~exceptions.NotImplementedError`.

        .. note:: This feature requires Django 1.6 or newer.

    .. method:: create(self, **kwargs)
    
        Creates a new instance using the kwargs given. If :attr:`_language_code`
        is not set and language_code is not in kwargs, it uses
        :func:`~django.utils.translation.get_language` to get the current
        language and injects that into kwargs.
        
        This causes two queries as opposed to the one by the normal queryset.
        
        Returns the newly created (combined) instance.

        .. note:: It is an error to call ``create`` with no ``language_code``
                  on a queryset whose :attr:`_language_code` is ``'all'``.
                  Doing so will raise a :exc:`~exceptions.ValueError`.

    .. method:: bulk_create(self, objs, batch_size=None)

        Not implemented yet and unlikely to be due to inherent limitations of
        multi-table inserts.

    .. method:: update_or_create(self, defaults=None, **kwargs)

        Not implemented yet.

    .. method:: get(self, *args, **kwargs)
    
        Gets a single instance from this queryset using the args and kwargs
        given. The args and kwargs are translated using
        :meth:`_translate_args_kwargs`.
        
        If a language code is given in the kwargs, it calls :meth:`language`
        using the language code provided. If none is given in kwargs, it uses
        :meth:`_find_language_code` on the
        :class:`~django.db.models.Q` objects given in args. If no
        args were given or they don't contain a language code, it searches the
        :class:`django.db.models.sql.where.WhereNode` objects on the current
        queryset for language codes. If none was found, it will use the language
        of this queryset from :attr:`_language_code`, or the current language
        as returned by :func:`~django.utils.translation.get_language` of that is None.
        
        Returns a (combined) instance if one can be found for the filters given,
        otherwise raises an appropriate exception depending on whether no or
        multiple objects were found.

        .. warning:: It is an error to pass `language_code` in a Q object if a
                     :meth:`select_related` clause was enabled on this queryset.
                     Doing so will raise an :exc:`~exceptions.AssertionError`.
     
    .. method:: get_or_create(self, **kwargs)
    
        Will try to fetch the translated instance for the kwargs given.
        
        If it can't find it, it will try to find a shared instance (using
        :meth:`_splitkwargs`). If it finds a shared instance, it will create
        the translated instance. If it does not find a shared instance, it will
        create both.
        
        Returns a tuple of a (combined) instance and a boolean flag which is
        ``False`` if it found the instance or ``True`` if it created **either**
        the translated or both instances.

    .. method:: filter(self, *args, **kwargs)
        
        Translates args and kwargs using :meth:`_translate_args_kwargs` and
        calls the superclass using the new args and kwargs.

    .. method:: aggregate(self, *args, **kwargs)
    
        Loops through the passed aggregates and translates the fieldnames using
        :meth:`_translate_fieldnames` and calls the superclass

    .. method:: latest(self, field_name=None)
    
        Translates the fieldname (if given) using :attr:`field_translator` and
        calls the superclass.

    .. method:: earliest(self, field_name=None)

        .. versionadded:: 0.4

        Translates the fieldname (if given) using :attr:`field_translator` and
        calls the superclass.

        Only defined if django version is 1.6 or newer.

    .. method:: in_bulk(self, id_list)

        .. versionadded:: 0.4

        Retrieves the objects, building a dict from :meth:`iterator`.

    .. method:: delete(self)
    
        Deletes the :term:`Shared Model` using :meth:`_get_shared_queryset`.
    
    .. method:: delete_translations(self)
    
        Deletes the translations (and **only** the translations) by first
        breaking their relation to the :term:`Shared Model` and then calling the
        delete method on the superclass. This uses two queries.
        
    .. method:: update(self, **kwargs)
    
        Updates this queryset using kwargs. Calls :meth:`_split_kwargs` to get
        two dictionaries holding only the shared or translated fields
        respectively. If translated fields are given, calls the superclass with
        the translated fields. If shared fields are given, uses
        :meth:`_get_shared_queryset` to update the shared fields.
        
        If both shared and translated fields are updated, two queries are
        executed, if only one of the two are given, one query is executed.
        
        Returns the count of updated objects, which if both translated and
        shared fields are given is the sum of the two update calls. 

    .. method:: values(self, *fields)
    
        Translates fields using :meth:`_translate_fieldnames` and calls the
        superclass.

    .. method:: values_list(self, *fields, **kwargs)
    
        Translates fields using :meth:`_translate_fieldnames` and calls the
        superclass.

    .. method:: dates(self, field_name, kind, order='ASC')
    
        Translates fields using :meth:`_translate_fieldnames` and calls the
        superclass.

    .. method:: datetimes(self, field_name, *args, **kwargs)

        Translates fields using :meth:`_translate_fieldnames` and calls the
        superclass.

        Only defined if django version is 1.6 or newer.

    .. method:: exclude(self, *args, **kwargs)
    
        Works like :meth:`filter`.

    .. method:: complex_filter(self, filter_obj)
    
        Not really implemented yet, but if filter_obj is an empty dictionary it
        just returns this queryset, since this is required to get admin to work.

    .. method:: annotate(self, *args, **kwargs)
    
        Not implemented yet.

    .. method:: order_by(self, *field_names)
    
        Translates fields using :meth:`_translate_fieldnames` and calls the
        superclass.
    
    .. method:: reverse(self)
    
        Calls the superclass.

    .. method:: defer(self, *fields)
    
        Not implemented yet.

    .. method:: only(self, *fields)
    
        Not implemented yet.
    
    .. method:: _clone(self, klass=None, setup=False, **kwargs)
    
        Injects *_local_field_names*, *_field_translator*, *_language_code*,
        and *shared_model* into *kwargs*. If a *klass* is
        given, calls :meth:`_get_class` to get a mixed class if necessary.
        
        Calls the superclass with the new *kwargs* and *klass*.
    
    .. method:: iterator(self)
    
        Iterates using the iterator from the superclass, if the objects yielded
        have a master, it yields a combined instance, otherwise the instance
        itself to enable non-cascading deletion.
        
        Interestingly, implementing the combination here also works for
        :meth:`get` and :meth:`__getitem__`. This is because the former uses the
        latter, which in turn fetches results from an iterator.


******************
TranslationManager
******************

.. class:: TranslationManager

    Manager to be used on :class:`hvad.models.TranslatableModel`.
    
    .. attribute:: translations_model
    
        The :term:`Translations Model` for this manager.

    .. attribute:: queryset_class

        The QuerySet for this manager, used by the :meth:`language` method.
        Overwrite to use a custom queryset. Your custom
        queryset class must inherit :class:`TranslationQueryset`. Defaults to
        :class:`TranslationQueryset`.

    .. attribute:: fallback_class

        The QuerySet for this manager, used by the :meth:`untranslated` method.
        Overwrite to use a custom queryset. Defaults to :class:`FallbackQueryset`.

    .. attribute:: default_class

        The QuerySet for this manager, used by the :meth:`get_queryset` method
        and generally any query that does not invoke either :meth:`language` or
        :meth:`untranslated`. Overwrite to use a custom queryset. Defaults to
        :class:`~django.db.models.query.QuerySet`.

    .. method:: language(self, language_code=None)
    
        Instanciates a :class:`TranslationQueryset` from :attr:`queryset_class` and calls
        :meth:`TranslationQueryset.language` on that queryset. This type of queryset
        will filter by language, returning only objects that have a translation
        in the specified language. Translated fields will be available on the
        objects, in the specified language.
    
    .. method:: untranslated(self)
    
        Returns an instance of :class:`FallbackQueryset` for this manager, or any
        custom queryset defined by :attr:`fallback_class`. This type of
        queryset will load translations using fallbacks if current language is
        not available. It can generate a lot a queries, use with caution.

    .. method:: get_queryset(self)
    
        Returns a vanilla, non-translating queryset for this manager. It uses
        the default :class:`~django.db.models.query.QuerySet` or any custom
        queryset defined by :attr:`default_class`.

        Instances returned will not have translated fields, and attempts to access them
        will result in an exception being raised. See :meth:`language` and :meth:`untranslated`
        to access translated fields.

        It is possible to override this behavior by setting :attr:`default_class`
        to :class:`TranslationQueryset`, :class:`FallbackQueryset` or any queryset
        that has a translation-aware implementation.
    
    .. method:: contribute_to_class(self, model, name)
    
        Contributes this manager onto the class.


****************
FallbackQueryset
****************

.. class:: FallbackQueryset

    .. deprecated:: 1.4

    A queryset that can optionally use fallbacks and by default only fetches the
    :term:`Shared Model`.

    There are actually two underlying implementations, the ``LegacyFallbackQueryset``
    and the ``SelfJoinFallbackQueryset``. Implementation is chosen at initialization
    based on the ``HVAD_LEGACY_FALLBACKS`` setting. It defaults to ``False``
    (use SelfJoin) on Django 1.6 and newer, and ``True`` (use Legacy) on older
    versions.

    The ``LegacyFallbackQueryset`` generates lots of queries as it walks through
    batches of models, fetches their translations and matches them onto the models.

    The ``SelfJoinFallbackQueryset`` uses a single self outer join to achieve the same
    result in only one (complex) query. Performance is good as the number of items
    per model in the cross-product is limited to the number of languages that
    Django supports. Implementation digs deeper into Django internals, though.

    .. attribute:: _translation_fallbacks
    
        List of fallbacks to use (or ``None``).
    
    .. method:: iterator(self)
    
        If :attr:`_translation_fallbacks` is set, it iterates using the
        superclass and tries to get the translation using the order of
        language codes defined in :attr:`_translation_fallbacks`. As soon as it
        finds a translation for an object, it yields a combined object using
        that translation. Otherwise yields an uncombined object. Due to the way
        this works, it can cause **a lot** of queries and this should be
        improved if possible.
        
        If no fallbacks are given, it just iterates using the superclass. 
    
    .. method:: use_fallbacks(self, *fallbacks)
    
        .. deprecated:: 1.4

        If this method gets called, :meth:`iterator` will use the fallbacks
        defined here. `None` value will be replaced with current language at
        query evaluation, as returned by :func:`~django.utils.translation.get_language`.
        If not fallbacks are given, :data:`FALLBACK_LANGUAGES` will be used,
        with current language prepended.

        This method has been superseded by :meth:`~hvad.manager.TranslationQueryset.fallbacks`
        and will be removed when support for Django 1.4 is dropped.

    .. method:: _clone(self, klass=None, setup=False, **kwargs)
    
        Injects *translation_fallbacks* into *kwargs* and calls the superclass.


************************
TranslationAwareQueryset
************************

.. class:: TranslationAwareQueryset

    .. attribute:: _language_code
    
        The language code of this queryset.

    .. method:: _translate_args_kwargs(self, *args, **kwargs)
    
        Calls :meth:`language` using :attr:`_language_code`
        as an argument.
    
        Translates *args* and *kwargs* into translation aware *args* and
        *kwargs* using :func:`hvad.fieldtranslator.translate` by iterating over
        the *kwargs* dictionary and translating it's keys and recursing over the
        :class:`~django.db.models.Q` objects in *args* using
        :meth:`_recurse_q`. 
        
        Returns a triple of *newargs*, *newkwargs* and *extra_filters* where
        *newargs* and *newkwargs* are the translated versions of *args* and
        *kwargs* and *extra_filters* is a
        :class:`~django.db.models.Q` object to use to filter for the
        current language. 

    .. method:: _recurse_q(self, q)
    
        Recursively translate the keys in the
        :class:`~django.db.models.Q` object given using
        :func:`hvad.fieldtranslator.translate`. For more information about
        :class:`~django.db.models.Q`, see
        :meth:`TranslationQueryset._recurse_q`.
        
        Returns a tuple of *q* and *language_joins* where *q* is the translated
        :class:`~django.db.models.Q` object and *language_joins* is
        a list of extra language join filters to be applied using the current
        language.
    
    .. method:: _translate_fieldnames(self, fields)
    
        Calls :meth:`language` using :attr:`_language_code`
        as an argument.
        
        Translates the fieldnames given using
        :func:`hvad.fieldtranslator.translate`
        
        Returns a tuple of *newfields* and *extra_filters* where *newfields* is
        a list of translated fieldnames and *extra_filters* is a
        :class:`~django.db.models.Q` object to be used to filter for
        language joins. 

    .. method:: language(self, language_code=None)
    
        Sets the :attr:`_language_code` attribute either to the language given
        with *language_code* or by getting the current language from
        :func:`~django.utils.translation.get_language`. Unlike
        :meth:`TranslationQueryset.language`, this does not actually filter by
        the language yet as this happens in :meth:`_filter_extra`.
    
    .. method:: get(self, *args, **kwargs)
    
        Gets a single object from this queryset by filtering by *args* and
        *kwargs*, which are first translated using
        :meth:`_translate_args_kwargs`. Calls :meth:`_filter_extra` with the
        *extra_filters* returned by :meth:`_translate_args_kwargs` to get a
        queryset from the superclass and to call that queryset.
        
        Returns an instance of the model of this queryset or raises an
        appropriate exception when none or multiple objects were found. 

    .. method:: filter(self, *args, **kwargs)
    
        Filters the queryset by *args* and *kwargs* by translating them using
        :meth:`_translate_args_kwargs` and calling :meth:`_filter_extra` with
        the *extra_filters* returned by :meth:`_translate_args_kwargs`. 
    
    .. method:: aggregate(self, *args, **kwargs)
    
        Not implemented yet.

    .. method:: latest(self, field_name=None)
    
        If a fieldname is given, uses :func:`hvad.fieldtranslator.translate` to
        translate that fieldname. Calls :meth:`_filter_extra` with the
        *extra_filters* returned by :func:`hvad.fieldtranslator.translate` if it
        was used, otherwise with an empty
        :class:`~django.db.models.Q` object.

    .. method:: in_bulk(self, id_list)
    
        Not implemented yet

    .. method:: values(self, *fields)
    
        Calls :meth:`_translate_fieldnames` to translated the fields. Then
        calls :meth:`_filter_extra` with the *extra_filters* returned by
        :meth:`_translate_fieldnames`.

    .. method:: values_list(self, *fields, **kwargs)
    
        Calls :meth:`_translate_fieldnames` to translated the fields. Then
        calls :meth:`_filter_extra` with the *extra_filters* returned by
        :meth:`_translate_fieldnames`.

    .. method:: dates(self, field_name, kind, order='ASC')
    
        Not implemented yet.

    .. method:: exclude(self, *args, **kwargs)
        
        Not implemented yet.

    .. method:: complex_filter(self, filter_obj)
    
        Not really implemented yet, but if *filter_obj* is an empty dictionary
        it just returns this queryset, to make admin work.

    .. method:: annotate(self, *args, **kwargs)
    
        Not implemented yet.

    .. method:: order_by(self, *field_names)
    
        Calls :meth:`_translate_fieldnames` to translated the fields. Then
        calls :meth:`_filter_extra` with the *extra_filters* returned by
        :meth:`_translate_fieldnames`.
    
    .. method:: reverse(self)
    
        Not implemented yet.

    .. method:: defer(self, *fields)
    
        Not implemented yet.

    .. method:: only(self, *fields)
        
        Not implemented yet.
    
    .. method:: _clone(self, klass=None, setup=False, **kwargs)
    
        Injects *_language_code* into *kwargs* and calls the superclass.
    
    .. method:: _filter_extra(self, extra_filters)
    
        Filters this queryset by the :class:`~django.db.models.Q`
        object provided in *extra_filters* and returns a queryset from the
        superclass, so that the methods that call this method can directely
        access methods on the superclass to reduce boilerplate code.

        .. warning:: This internal method returns a ``super()`` proxy object,
                     be sure to understand the implications before using it.
    
***********************
TranslationAwareManager
***********************

.. class:: TranslationAwareManager

    .. method:: get_queryset(self)

        Returns an instance of :class:`TranslationAwareQueryset`.
