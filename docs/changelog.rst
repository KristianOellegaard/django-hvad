.. _changelog:

#########
Changelog
#########

.. glossary::
    :sorted:

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