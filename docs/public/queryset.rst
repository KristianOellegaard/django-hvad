############
Queryset API
############

If you do not need to do fancy things such as custom querysets and are not in
the process of optimizing your queries yet, you can skip straight to next
section, to start using your translatable models to :doc:`build some forms <forms>`.

The queryset API is at the heart of hvad. It provides the ability to filter
on translatable fields and retrieve instances along with their translations.

The :ref:`TranslationQueryset <TranslationQueryset-public>`, is for working with
instances translated in a specific language. It is the one used when calling
:meth:`TranslationManager.language() <hvad.manager.TranslationManager.language>`.

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
    with an empty argument list, the ``FALLBACK_LANGUAGES`` :ref:`setting <settings>`
    will be used.

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

----------

Next, we will use our models and queries to :doc:`build some forms <forms>`.
