#########
Migration
#########

.. _migrate-hvad-1:

******************************
Migrating from django-hvad 1.x
******************************

For the first refactor of hvad, the API had to be slightly altered
to make use of the newer possibilies enabled by Django evolutions.
Most code written for the latest django-hvad 1.x series should
work as-is, but some corner cases, especially code fragments that
do translation-aware model management, have to be updated.

Settings
========

To reduce namespace pollution, and allow different settings for
interface and model translations, :ref:`hvad settings <settings>`
now all live under a ``HVAD`` entry in django settings.

In addition, some settings have changed and must be updated:

    * ``TABLE_NAME_SEPARATOR`` has been changed into
      ``TABLE_NAME_FORMAT``. It is no longer just the separator,
      but a full *%s-style* formatting string, allowing more customization.

      For instance, if you used to have ``TABLE_NAME_SEPARATOR = '_foo_'``,
      you must replace it with ``TABLE_NAME_FORMAT = '%s_foo_translation'``.

    * ``AUTOLOAD_TRANSLATIONS`` is a new setting that enables
      backwards-compatible loading of translations. In hvad2, by default,
      accessing a translated field when no translation is loaded no longer
      causes an automatic attempt to load one. This setting enables
      that behavior again, for compatibility with code relying on it.

      Please note this is intended as a compatibility setting, which will be removed
      in the future.

Models
======

Model API has been simplified thanks to the new features of
:ref:`translations <model-translations>` accessor. Its actual name is
whatever name you assigned your :class:`~hvad.models.TranslatedFields` to. Here,
code samples will assume you named it ``translations``.

The new features should simplify your code a lot when it comes to
manually handling translations and leveraging Django caching and
prefetching while working on multilingual models. Some incompatible changes
also had to be performed, and existing code must be updated in the following way:

.. class:: TranslatableModel(*args, **kwargs)

    Invoking a translatable model constructor now always instantiates and
    activates a translation. If a ``language_code`` argument is passed,
    the translation will be in that language, otherwise it will be in
    :func:`current language <django.utils.translation.get_language>`.

    This behavior can be overriden by passing the special value
    :data:`~hvad.models.NoTranslation` as ``language_code``.
    Tread carefully as a translatable model without any translation
    is now an error.

.. attribute:: instance.language_code

    This attribute used to trigger automatic loading of a translation if
    none was currently active. It no longer does, and returns ``None``
    in that case.

    The automatic loading was seldom used on this special attribute,
    and removing it allows translation-aware code to easily test current
    language without triggering a database query::

        if instanceA.language_code != instanceB.language_code:
            print('Not same translation')

.. method:: instance.lazy_translation_getter('field_name', 'default_value')

    This method has been removed completely. It can be safely replaced with::

        instance.field_name if instance.translations.active else 'default_value'

    This is the preferred replacement, although it will behave differently
    when a translation is active *but* has no ``field_name`` attribute.
    In that case, it will raise an :exc:`~exceptions.AttributeError`, which
    is usually the desired behavior. If strictly identical behavior to old
    ``lazy_translation_getter`` is needed, use this instead::

        getattr(instance.translations.active, 'field_name', 'default_value')

.. method:: instance.safe_translation_getter('field_name', 'default_value')

    This method has been removed completely. As untranslated instances are
    now forbidden and on-the-fly re-loading is being phased out in favor
    of systematic prefetching for improved performance, the preferred
    replacement is::

        instance.field_name if instance.translations.active else 'default_value'

    Note that this will no longer try to load translations and pick one
    from database. Translations should now be prefetched at query time.
    In the rare event that the old automatic translation picking is
    desired, it must be done explicitly. The new
    :func:`~hvad.utils.translation_rater` helper comes in handy for this task::

        instance.translations.activate(max(instance.translations.all(), key=translation_rater()))

    This sample will take advantage of prefetched translations.

.. method:: instance.get_available_languages()

    This method has been renamed and moved to the translations accessor::

        instance.translations.all_languages()

.. method:: instance.translate('language_code')

    This method no longer returns ``self``. This is to follow the general
    python paradigm that methods taking action should not return anything.

    Therefore, any code looking like this should be split into separate
    statements::

        instance.translate('en').do_something()
        # BECOMES
        instance.translate('en')
        instance.do_something()

Queries
=======

Due to some limitations on the way queries are combined in Django ORM, one muse be careful
when filtering on translated fields. Two separate ``filter()`` calls will result on
filtering separately. Under the hood, translated fields are accessed through a ``JOIN``
query, and each ``filter()`` call has its own context. That is::

        # Query 1
        MyModel.objects.language('all').filter(foo='baz', bar=42)

        # Query 2
        MyModel.objects.language('all').filter(foo='baz').filter(bar=42)

Assuming both ``foo`` and ``bar`` are translated fields, then:

    * Query #1 returns objects that have a language in which **both** ``foo`` and ``bar`` match.
    * Query #2 returns objects that have a language in which **either** ``foo`` or ``bar`` matches.

This is similar to how Django behaves with joins (because this is how the query is handled).
Queries that work on a single language are not affected, though depending on the database engine
the double-join of query #2 might degrade performance.

