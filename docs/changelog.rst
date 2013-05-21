.. _changelog:

#########
Changelog
#########

.. glossary::
    :sorted:
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
