############
Queryset API
############

If you do not need to do fancy things such as custom querysets and are not in
the process of optimizing your queries yet, you can skip straight to next
section, to start using your translatable models to :doc:`build some forms <forms>`.

The queryset API is at the heart of hvad. It provides the ability to filter
on translatable fields and retrieve instances along with their translations.
They come in two flavors:

- The :ref:`TranslationQueryset <TranslationQueryset-public>`, for working with
  instances translated in a specific language. It is the one used when calling
  :meth:`TranslationManager.language() <hvad.manager.TranslationManager.language>`.
- The :ref:`FallbackQueryset <FallbackQueryset-public>`, for working with
  all instances regardless of their language, and eventually loading translations
  using a fallback algorithm. It is the one used when calling
  :meth:`TranslationManager.untranslated() <hvad.manager.TranslationManager.untranslated>`.

.. note::
    It is possible to :ref:`override the querysets <custom-managers>` used on
    a model's manager.

.. _TranslationQueryset-public:

*******************
TranslationQueryset
*******************

The TranslationQueryset works on a translatable model, limiting itself to instances
that have a translation in a specific language. Its API is almost identical to
the regular Django :class:`~django.db.models.query.QuerySet`.

New and Changed Methods
=======================

language
--------

.. _language-public:

.. method:: language(language_code=None)

    Sets the language for the queryset to either the given language code or
    the currently active language if None. Language resolution will be deferred
    until the query is evaluated.

    This filters out all instances that are not translated in the given language,
    and makes translatable fields available on the query results.

    The special value ``'all'`` disables language filtering. This means that objects
    will be returned once per language in which they match the query, with
    the appropriate translation loaded.

    .. note:: support for :ref:`select_related() <select_related-public>` in combination
              with ``language('all')`` is experimental. Please check the generated
              queries and open an issue if you have any problem. Feedback
              is appreciated as well.

fallbacks
---------

.. _fallbacks-public:

.. method:: fallbacks(*languages)

    .. versionadded:: 0.6

    Enables fallbacks on the queryset. When the queryset has fallbacks enabled,
    it will try to use fallback languages if an object has not translation
    available in the language given to :ref:`language() <language-public>`.

    The `languages` arguments specified the languages to use, priorized from
    first to last. Special value `None` will be replaced with current language
    as returned by :func:`~django.utils.translation.get_language`. If called
    with an empty argument list, the :setting:`LANGUAGES` setting will be used.

    If an instance has no translation in the
    :ref:`language() <language-public>`-specified language,
    nor in any of the languages given to ``fallbacks()``, an arbitrary
    translation will be picked.

    Passing the single value ``None`` alone will disable fallbacks.

    .. note:: This feature requires Django 1.6 or newer.

delete_translations
-------------------

.. method:: delete_translations()

    Deletes all :term:`Translations Model` instances matched by a queryset, without
    deleting the :term:`Shared Model` instances.

    This can be used to target specific translations of specific objects for deletion.
    For instance::

        # Delete English translation of all objects that have field == "foo"
        MyModel.objects.language('en').filter(field='foo').delete_translations()

        # Delete all translations but English for object with id 42
        MyModel.objects.language('all').exclude(language_code='en').filter(pk=42).delete_translations()

    .. warning:: It is an error to delete all translations of an instance. This will
                 cause the object to be unreachable through translation-aware queries
                 and invisible in the admin panel.

                 If you delete all translations and re-create one immediately after,
                 remember to enclose the whole process in a transaction to avoid
                 the possibility of leaving the object unreachable.

.. _select_related-public:

select_related
--------------

.. method:: select_related(*fields)

    Inherited from :meth:`~django.db.models.query.QuerySet.select_related`.

    The ``select_related`` method also selects translations of translatable
    models when it encounters some.

    .. note:: support for ``select_related`` in combination with
              ``language('all')`` is experimental. Please check the generated
              queries and open an issue if you have any problem. Feedback
              is appreciated as well.


Not implemented public queryset methods
=======================================

The following are methods on a queryset which are public APIs in Django, but are
not implemented (yet) in django-hvad:

* :meth:`~hvad.manager.TranslationQueryset.bulk_create`
* :meth:`~hvad.manager.TranslationQueryset.update_or_create`
* :meth:`~hvad.manager.TranslationQueryset.complex_filter`
* :meth:`~hvad.manager.TranslationQueryset.defer`
* :meth:`~hvad.manager.TranslationQueryset.only`

Using any of these methods will raise a :exc:`~exceptions.NotImplementedError`.

Performance consideration
=========================

While most methods on :class:`~hvad.manager.TranslationQueryset` run
using the same amount of queries as if they were untranslated, they all do
slightly more complex queries (one extra join).

The following methods run two queries where standard querysets would run one:

* :meth:`~hvad.manager.TranslationQueryset.create`
* :meth:`~hvad.manager.TranslationQueryset.update` (only if both translated and
  untranslated fields are updated at once)

:meth:`~hvad.manager.TranslationQueryset.get_or_create` runs one query if the
object exists, three queries if the object does not exist in this language, but
in another language and four queries if the object does not exist at all. It
will return ``True`` for created if either the shared or translated instance
was created.


.. _FallbackQueryset-public:

****************
FallbackQueryset
****************

.. deprecated:: 1.4

This is a queryset returned by :meth:`~hvad.manager.TranslationManager.untranslated`,
which can be used both to get the untranslated parts of models only or to use
fallbacks for loading a translation based on a priority list of languages.
By default, only the untranslated parts of models are retrieved from
the database, and accessing translated field will trigger an additional query
for each instance.

.. warning:: You may not use any translated fields in any method on this
             queryset class.

.. warning:: If you have a default :attr:`~django.db.models.Options.ordering`
             defined on your model and it includes any translated field, you
             must specify an ordering on every query so as not to use the
             translated fields specified by the default ordering.

New Methods
===========

use_fallbacks
-------------

.. versionchanged:: 0.5

.. method:: use_fallbacks(*fallbacks)

    .. deprecated:: 1.4

    Returns a queryset which will use fallbacks to get the translated part of
    the instances returned by this queryset. If ``fallbacks`` is given as a
    tuple of language codes, it will try to get the translations in the order
    specified, replacing the special `None` value with the current language at
    query evaluation, as returned by :func:`~django.utils.translation.get_language`.
    Otherwise the order of your LANGUAGES setting will be used, prepended with
    current language.

    This method is now deprecated, and one should use
    :ref:`TranslationQueryset.fallbacks() <fallbacks-public>` for an equivalent
    feature.
    
    .. warning:: Using fallbacks with a version of Django older than 1.6 will
                 cause **a lot** of queries! In the worst
                 case 1 + (n * x) with n being the amount of rows being fetched
                 and x the amount of languages given as fallbacks. Only ever use
                 this method when absolutely necessary and on a queryset with as
                 few results as possible.

                 .. versionchanged:: 0.5
                    Fallbacks were reworked, so that when running
                    on Django 1.6 or newer, only one query is needed.

Not implemented public queryset methods
=======================================

The following are methods on a queryset which are public APIs in Django, but are
not implemented on fallback querysets.

* :meth:`~django.db.models.query.QuerySet.aggregate`
* :meth:`~django.db.models.query.QuerySet.annotate`
* :meth:`~django.db.models.query.QuerySet.defer`
* :meth:`~django.db.models.query.QuerySet.only`

----------

Next, we will use our models and queries to :doc:`build some forms <forms>`.
