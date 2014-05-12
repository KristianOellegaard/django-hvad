############
Queryset API
############

.. _TranslationQueryset-public:

.. note::
    You can select a custom queryset to use on your manager, by defining the attribute
    :attr:`~hvad.manager.TranslationManager.queryset_class` on the manager class.

*******************
TranslationQueryset
*******************

This is the default queryset used by the :class:`~hvad.manager.TranslationManager`.

Performance consideration
=========================

While most methods on :class:`~hvad.manager.TranslationQueryset` querysets run
using the same amount of queries as if they were untranslated, they all do
slightly more complex queries (one extra join).

The following methods run two queries where standard querysets would run one:

* :meth:`hvad.manager.TranslationQueryset.create`
* :meth:`hvad.manager.TranslationQueryset.update` (only if both translated and 
  untranslated fields are updated at once)
  
:meth:`hvad.manager.TranslationQueryset.get_or_create` runs one query if the
object exists, three queries if the object does not exist in this language, but
in another language and four queries if the object does not exist at all. It
will return ``True`` for created if either the shared or translated instance
was created.


New methods
===========

Methods described here are unique to django-hvad and cannot be used on normal
querysets.


language
--------

.. method:: language(language_code=None)
    
    Sets the language for the queryset to either the language code defined or
    the currently active language. This method should be used for all queries
    for which you want to have access to all fields on your model.


.. _TranslationQueryset.untranslated-public:

untranslated
------------

.. method:: untranslated

    Returns a :class:`hvad.manager.FallbackQueryset` instance which by default
    does not fetch any translations. This is useful if you want a list of
    :term:`Shared Model` instances, regardless of whether they're translated in
    any language.

    .. note:: No translated fields can be used in any method of the queryset
              returned my this method. See :ref:`FallbackQueryset-public`

    .. note:: This method is only available on the manager directly, not on a
              queryset.


delete_translations
-------------------

.. method:: delete_translations

    Deletes all :term:`Translations Model` instances in a queryset, without
    deleting the :term:`Shared Model` instances.


Not implemented public queryset methods
=======================================

The following are methods on a queryset which are public APIs in Django, but are
not implemented (yet) in django-hvad:

* :meth:`hvad.manager.TranslationQueryset.in_bulk`
* :meth:`hvad.manager.TranslationQueryset.complex_filter`
* :meth:`hvad.manager.TranslationQueryset.annotate`
* :meth:`hvad.manager.TranslationQueryset.reverse`
* :meth:`hvad.manager.TranslationQueryset.defer`
* :meth:`hvad.manager.TranslationQueryset.only`

Using any of these methods will raise a :exc:`NotImplementedError`.


.. _FallbackQueryset-public:

****************
FallbackQueryset
****************

This is a queryset returned by :ref:`TranslationQueryset.untranslated-public`,
which can be used both to get the untranslated parts of models only or to use
fallbacks. Only the untranslated parts of models are retrieved from
the database, and accessing translated field will trigger an additional query
for each instance.

.. warning:: You may not use any translated fields in any method on this
             queryset class.

New Methods
===========


use_fallbacks
-------------

.. method:: use_fallbacks(*fallbacks)

    Returns a queryset which will use fallbacks to get the translated part of
    the instances returned by this queryset. If ``fallbacks`` is given as a
    tuple of language codes, it will try to get the translations in the order
    specified. Otherwise the order of your LANGUAGES setting will be used.
    
    .. warning:: Using fallbacks will cause **a lot** of queries! In the worst
                 case 1 + (n * x) with n being the amount of rows being fetched
                 and x the amount of languages given as fallbacks. Only ever use
                 this method when absolutely necessary and on a queryset with as
                 few results as possibel.
