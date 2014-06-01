.. _changelog:

#########
Changelog
#########

.. glossary::

    0.4.1
        Fixes:

        - Translations no longer remain in database when deleted depending on
          the query that deleted them (bug :issue:`183`).
        - :meth:`~hvad.models.TranslatableModel.get_available_languages` now
          uses translations if they were prefetched with
          :meth:`~django.db.models.query.QuerySet.prefetch_related`. This
          dramatically cuts down the number of queries that
          :meth:`~hvad.admin.TranslatableAdmin.all_translations` generate
          (bug :issue:`97`).

    0.4.0
        New Python and Django versions supported:

        - django-hvad now supports Django 1.7 running on Python 2.7, 3.3 and 3.4.
        - django-hvad now supports Django 1.6 running on Python 2.7 and 3.3.

        New features:

        - :class:`~hvad.manager.TranslationManager`'s queryset class can now be overriden by
          setting its :attr:`~hvad.manager.TranslationManager.queryset_class` attribute.
        - Proxy models can be used with django-hvad. This is a new feature, please
          use with caution and report any issue on github.
        - :class:`~hvad.admin.TranslatableAdmin`'s list display now has direct links
          to each available translation.
        - Instance's translated fields are now available to the model's
          :meth:`~django.db.models.Model.save` method when saving a
          :class:`~hvad.forms.TranslatableModelForm`.
        - Accessing a translated field on an untranslated instance will now
          raise an :exc:`AttributeError` with a helpful message instead of
          letting the error bubble up from the ORM.

        Deprecation list:

        - Catching :exc:`~django.core.exceptions.ObjectDoesNotExist` when accessing
          a translated field on an instance is deprecated. In case no translation
          is loaded and none exists in database for current language, an :exc:`AttributeError`
          is raised instead. For the transition, both are supported until next release.

        Fixes:

        - No more deprecation warnings when importing only from :mod:`hvad`.
        - :class:`~hvad.admin.TranslatableAdmin` now generates relative URLs instead
          of absolute ones, enabling it to work behind reverse proxies.
        - django-hvad does not depend on the default manager being named
          'objects' anymore.
        - Q objects now work properly with :class:`~hvad.manager.TranslationQueryset`.

        Removal of the old :mod:`nani` aliases was postponed until next release.

    0.3.0
        django-hvad is now django 1.5 compatible. Dropped support for django 1.2.

        In next release, the old 'nani' module will be removed.

    0.2.0
        The package is now called 'hvad'. Old imports should result in an import error.

        Fixed django 1.4 support

        Fixed a number of minor issues

    0.1.4
        Introduces :meth:`lazy_translation_getter`

    0.1.3
        Introduces setting to configure the table name separator (unsurprisingly named ``NANI_TABLE_NAME_SEPARATOR``).
        The default is ``_``, to ensure schema compatibility with the deprecated ``django-multilingual-ng``.

        .. note::
            Until version 0.1, no separator was used. If you want to upgrade to 0.1.1, you'll either have to rename
            the tables manually or set ``NANI_TABLE_NAME_SEPARATOR`` to ``''`` in your settings.

    0.1
        Fixed a bug where inlines would break in case the master didnt have the same id as the translation.

    0.0.6
        The behaviour of the fallbacks are now slightly changed - if you use .use_fallbacks() it will no longer return untranslated instances.

    0.0.5
        Started changelog
