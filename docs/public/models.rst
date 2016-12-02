######
Models
######

.. contents::
    :depth: 1
    :local:

***************
Defining models
***************

Defining models with django-hvad is done by inheriting
:class:`~hvad.models.TranslatableModel`. Model definition works like in
regular Django, with the following additional features:

- Translatable fields can be defined on the model, by wrapping them in a
  :class:`~hvad.models.TranslatedFields` instance, and assigning it to an
  attribute on the model. That attribute will be used to access the
  :term:`translations <Translations Model>` of your model directly. Behind the
  scenes, it will be a reversed ForeignKey from the
  :term:`Translations Model` to your :term:`Shared Model`.
- Translatable fields can be used in the model options. For options that take
  groupings of fields (``unique_together`` and ``index_together``), each grouping
  may have either translatable or non-translatable fields, but not both.
- Special field ``language_code`` is automatically created by hvad, and may be used
  for defining ``unique_together`` constraints that are only unique per language.

A full example of a model with translations::

    from django.db import models
    from hvad.models import TranslatableModel, TranslatedFields

    class TVSeries(TranslatableModel):
        distributor = models.CharField(max_length=255)

        translations = TranslatedFields(
            title=models.CharField(max_length=100),
            subtitle=models.CharField(max_length=255),
            released=models.DateTimeField(),
        )
        class Meta:
            unique_together = [('title', 'subtitle'), ('title', 'language_code')]

.. note:: Using :class:`~django.db.models.ManyToManyField` as a translated field is
          not supported. It is not forbidden because some projects do use it, but
          doing so requires digging into hvad internals. See
          :ref:`this FAQ entry <no-translated-many>` for details.

.. note:: The :djterm:`Meta <meta-options>` class of the model may not use the
          translatable fields in :attr:`~django.db.models.Options.order_with_respect_to`.
.. note:: TranslatedFields cannot contain a field named ``master``, as this name
          is reserved by hvad to refer to the :term:`Shared Model`. Also, special
          field ``language_code`` can be overriden in order to set it to be a
          different type of field, or change its options.

***********************************
New and Changed Methods and Objects
***********************************

translate
=========

.. method:: translate(language_code)

    Prepares a new translation for this instance for the language specified.

    .. note:: This method does not perform any database queries. It assumes the
              translation does not exist. If it does exist, trying to save the
              instance will raise an :exc:`~django.db.IntegrityError`.

save
====

.. method:: save(force_insert=False, force_update=False, using=None, update_fields=None)

    Overrides :meth:`~django.db.models.Model.save`.

    This method runs an extra query to save the translation cached on
    this instance, if any translation was cached.

    It accepts both translated and untranslated fields in ``update_fields``.

    - If only untranslated fields are specified, the extra query will be skipped.
    - If only translated fields are specified, the shared model update will be skipped.
      Note that this means signals will not be triggered.

    The two queries are run in a single translation

.. _model-translations:

translations
============

.. versionadded:: 2.0

.. attribute:: translations

    The actual name of this attribute is that of the
    :class:`~hvad.models.TranslatedFields` instance. Third-party modules can
    get its name as ``Model._meta.translations_accessor``.
    It gives access to the
    :class:`~django.db.models.fields.related.RelatedManager` for
    :term:`translations <Translations Model>`. This manager includes the
    following additions:

    .. attribute:: model

        The underlying model class of translations for user code.
        Third-party modules should use ``Model._meta.translations_model`` instead.

    .. method:: prefetch(self, force_reload=False)

        Force loading of all translations for the instance. If they are
        already loaded, this is a no-op unless ``force_reload`` is ``True``.

        The cache used by this method is the same as the one used by
        :meth:`~django.db.models.query.QuerySet.prefetch_related`, so
        generally it is better to do ``.prefetch_related('translations')``
        when loading the model.

    .. method:: activate(self, language_or_translation)

        Sets the active translation for the instance. Possible values are:

            * ``None`` to unload any currently loaded translation and let
              the object without a translation.
            * A :term:`Translations Model` instance attached to this model, for
              instance one returned by ``instance.translations.all()``.
            * A language code to load the corresponding translation. This forces
              a calls to :meth:`prefetch`, then looks for a translation in
              loaded objects. Finally, if no translation is found in given
              language, raise a :exc:`~django.db.models.Model.DoesNotExist` exception.

    .. attribute:: active

        Returns the translation currently cached onto the instance, or ``None``
        if the instance has no translation cached.

    .. method:: get_language(self, language)

        Returns the :term:`Translations Model` instance for given language. Special
        value ``None`` is replaced with
        :func:`current language <django.utils.translation.get_language>`.

        If translations have been cached by :meth:`prefetch` or
        :meth:`~django.db.models.query.QuerySet.prefetch_related`, the cache is
        used. Otherwise, a database query is run, and the result is **not** cached.

    .. method:: all_languages(self)

        Returns a set of all language codes the instance has a translation for.
        As a set, it is not ordered, use :func:`sorted` built-in function to
        get a specific order.

        If translations have been cached by :meth:`prefetch` or
        :meth:`~django.db.models.query.QuerySet.prefetch_related`, the cache is
        used. Otherwise, a database query is run, and the result is **not** cached.

**********************
Working with relations
**********************

Foreign keys pointing to a :term:`Translated Model` always point to the
:term:`Shared Model`. It is, by design, not possible to have a foreign key to a
:term:`Translations Model`.

Please note that :meth:`~django.db.models.query.QuerySet.select_related` used on
a foreign key pointing from a :term:`normal model <Normal Model>` to a
:term:`translatable model <Translated Model>` does not span to its
:term:`translations <Translations Model>` and therefore accessing a translated
field over the relation will cause an extra query. Foreign keys from a
translatable model do not have this restriction.

If you wish to filter over a translated field over the relation from a
:term:`Normal Model` you have to use
:func:`~hvad.utils.get_translation_aware_manager` to get a manager that allows
you to do so. That function takes your model class as argument and returns a
manager that works with translated fields on related models.

**************************
Advanced Model Definitions
**************************

Abstract Models
===============

.. versionadded:: 0.5

:djterm:`Abstract models <abstract-base-classes>` can be used normally with hvad.
Untranslatable fields of the base models will remain untranslatable, while
translatable fields will be translatable on the concrete model as well::

    class Place(TranslatableModel):
        coordinates = models.CharField(max_length=64)
        translations = TranslatedFields(
            name=models.CharField(max_length=255),
        )
        class Meta:
            abstract = True

    class Restaurant(Place):
        score = models.PositiveIntegerField()
        translations = TranslatedFields()   # see note below

.. note:: The concrete models **must** have a :class:`~hvad.models.TranslatedFields`
          instance as one of their attributes. This is required because this
          attribute will be used to access the translations. It can be empty.

Proxy Models
============

.. versionadded:: 0.4

:djterm:`Proxy models <proxy-models>` can be used normally with hvad, with the
following restrictions:

- The ``__init__`` method of the proxy model will not be called when it is
  loaded from the database.
- As a result, the :attr:`~django.db.models.signals.pre_init` and
  :data:`~django.db.models.signals.post_init` signals will not be sent for
  the proxy model either.

The ``__init__`` method and signals for the concrete model will still be called.

Multi-table Inheritance
=======================

Unfortunately, multi-table inheritance is not supported, and unlikely to be.
Please read :issue:`230` about the issues with multi-table inheritance.

.. _custom-managers:

*****************************
Custom Managers and Querysets
*****************************

Custom Manager
==============

Vanilla :class:`managers <django.db.models.Manager>`, using vanilla
:class:`querysets <django.db.models.query.QuerySet>` can be used with translatable
models. However, they will not have access to translations or translatable fields.
Also, such a vanilla manager cannot serve as a
:djterm:`default manager <default managers>` for the model. The default manager
**must** be translation aware.

To have full access to translations and translatable fields, custom managers
must inherit :class:`~hvad.manager.TranslationManager` and custom querysets
must inherit either :class:`~hvad.manager.TranslationQueryset` (enabling the
use of :meth:`~hvad.manager.TranslationQueryset.language`). It is described in the
:doc:`dedicated section <queryset>`.

Custom Querysets
================

Once you have a custom queryset, you can use it to override the default ones
in your manager. This is where it is more complex than a regular manager:
:class:`~hvad.manager.TranslationManager` uses three types of queryset, that
can be overriden independently:

- :attr:`~hvad.manager.TranslationManager.queryset_class` must inherit
  :class:`~hvad.manager.TranslationQueryset`, and will be used for all queries
  that call the :meth:`~hvad.manager.TranslationManager.language` method.
- :attr:`~hvad.manager.TranslationManager.fallback_class` must **not** inherit
  :class:`~hvad.manager.TranslationQueryset`, and will be used for all queries
  that call the :meth:`~hvad.manager.TranslationManager.untranslated`
  method.
- :attr:`~hvad.manager.TranslationManager.default_class` may be any kind of
  queryset (a ``TranslationQueryset`` or a plain
  :class:`~django.db.models.query.QuerySet`). It will be used for all queries
  that call neither ``language`` nor ``untranslated``. Its default depends on
  the :ref:`USE_DEFAULT_QUERYSET <settings>` setting; see next section
  about overriding it.

As a convenience, it is possible to override the queryset at manager instanciation,
avoiding the need to subclass the manager::

    class TVSeriesTranslationQueryset(TranslationQueryset):
        def is_public_domain(self):
            threshold = datetime.now() - timedelta(days=365*70)
            return self.filter(released__gt=threshold)

    class TVSeries(TranslatableModel):
        # ... (see full definition in previous example)
        objects = TranslationManager(queryset_class=TVSeriesTranslationQueryset)

.. _override-default-queryset:

Overriding Default Queryset
===========================

.. versionadded:: 0.6

By default, the :class:`~hvad.manager.TranslationManager` returns a vanilla,
translation-unaware :class:`~django.db.models.query.QuerySet` when a query is
done without either :meth:`~hvad.manager.TranslationManager.language` or
:meth:`~hvad.manager.TranslationManager.untranslated`. This conservative
behavior makes it compatible with third party modules. It is, however, possible
to set it to be translation-aware by overriding it::

    class MyModel(TranslatableModel):
        objects = TranslationManager(default_class=TranslationQueryset)

This deeply changes key behaviors of the manager, with many benefits:

- The call to ``language()`` can be omitted, filtering on translations is
  implied in all queries that do not call ``untranslated()``.
  It is still possible to use it to set another language on the queryset.
- As a consequence, all third-party modules will only see objects in current
  language, unless they are hvad-aware.
- They will also gain access to translated fields.
- Queries that use :meth:`~django.db.models.query.QuerySet.prefetch_related` will
  prefetch the translation as well (in current language).
- Accessing a translatable model from a :class:`~django.db.models.ForeignKey` or a
  :class:`~django.contrib.contenttypes.fields.GenericForeignKey` will also load
  and cache the translation in current language.

In other terms, all queries become translation-aware by default.

.. warning:: Some third-party modules may break if they rely on the ability
             to see all objects. `MPTT`_, for instance, will corrupt its tree
             if some objects have no translation in current language.
             Use caution when combining this feature with other manager-altering
             modules.

.. _custom-translation-models:

Custom Translation Models
=========================

.. versionadded:: 1.5

It is possible to have :term:`translations <Translations Model>` use a custom base
class, by specifying a ``base_class`` argument to :class:`~hvad.models.TranslatedFields`.
This may be useful for advanced manipulation of translations, such as customizing some
model methods, for instance :meth:`~django.db.models.Model.from_db`::

    class BookTranslation(models.Model):
        @classmethod
        def from_db(cls, db, fields, values):
            obj = super(BookTranslation, self).from_db(cls, db, field, values)
            obj.loaded_at = timezone.now()
            return obj

        class Meta:
            abstract = True

    class Book(TranslatableModel):
        translations = TranslatedFields(
            base_class=BookTranslation,
            name=models.CharField(max_length=255),
        )

In this example, the ``Book``'s translation model will have ``BookTranslation`` as its
first base class, so every translation will have a ``loaded_at`` attribute when loaded
from the database. Keep in mind this attribute will *not* be available on the book itself,
but can be accessed through ``get_cached_translation(book).loaded_at``.

Such classes are inserted into the translations inheritance tree, so if some other model
inherits ``Book``, its translations will also inherit ``BookTranslation``.

--------

Next, we will detail the :doc:`translation-aware querysets <queryset>` provided
by hvad.

.. _MPTT: https://github.com/django-mptt/django-mptt/
