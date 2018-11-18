############
Installation
############


************
Requirements
************

* `Django`_ 1.8 to 1.11 using hvad < 2.0.
* `Django` 2.1 or higher for hvad ≥ 2.0.
* A Python version matching django's compatibility matrix.

************
Installation
************

Packaged version
================

.. highlight:: console

This is the recommended way. Install django-hvad using `pip`_ by running::

    pip install django-hvad

This will download the latest version from `pypi`_ and install it.

Then add ``'hvad'`` to your :std:setting:`INSTALLED_APPS`, and proceed to
:doc:`quickstart`.

Latest development version
==========================

.. highlight:: console

If you need the latest features from a yet unreleased version, or just like
living on the edge, install django-hvad using `pip`_ by running::

    pip install https://github.com/kristianoellegaard/django-hvad/tarball/master

This will download the development branch from `github`_ and install it.

Then add ``'hvad'`` to your :std:setting:`INSTALLED_APPS`, and proceed to
:doc:`quickstart`.

.. _settings:

Advanced settings
=================

Hvad settings live under a ``HVAD`` key in django settings. They are completely
optional, and most use cases are covered by defaults. The following
settings are recognized:

    * ``LANGUAGES``:

        List of languages to offer to the user in default forms and admin
        interface. Only language codes.

        Defaults to language codes of Django's :setting:`LANGUAGES`.

    * ``FALLBACK_LANGUAGES``:

        Ordered list of language codes to use when
        :ref:`fallbacks() <fallbacks-public>` is used with
        no arguments. Also used for scoring translations with
        :func:`~hvad.utils.translation_rater`.

        Defaults to ``LANGUAGES``

    * ``TABLE_NAME_FORMAT``:

        The string to use to form the table name of translation models.

        Defaults to ``%s_translation``.

    * ``AUTOLOAD_TRANSLATIONS``:

        Whether accessing a translated field with no translation cached should
        try to automatically load translation for current language from the
        database.

        The recommended value is ``False``, causing such an access to raise
        an :exc:`~exceptions.AttributeError` without hitting the database.

        Setting this to ``True`` will cause hvad to try to load a translation
        from the database for
        :func:`current language <django.utils.translation.get_language`. This
        is the behavior of hvad 1.x, and is mostly useful for porting legacy
        code to hvad 2.

        Defaults to ``False``.

    * ``USE_DEFAULT_QUERYSET``:

        Whether hvad should override the default queryset of translatable models.

        - If this setting is ``False``, then ``MyModel.objects.all()`` will be a
          plain, translation-unaware, Django :class:`~django.db.models.query.QuerySet`.
          Translation-awareness must be activated using ``MyModel.objects.language()``.
          This enables better interoperability with third-party apps.

        - If this setting is ``True``, then ``MyModel.objects.all()`` will be
          translation-aware, exactly like ``MyModel.objects.language()``. This makes
          translated fields visible to third-party apps, which is convenient but
          might break some.

        Defaults to ``False``. Can be overridden on a model-by-model basis by
        specifying ``default_class = QuerySet`` or
        ``default_class = TranslationQuerySet`` while instanciating the model's manager.

.. _pip: http://pypi.python.org/pypi/pip
.. _pypi: https://pypi.python.org/pypi/django-hvad
.. _github: https://github.com/kristianoellegaard/django-hvad
.. _Django: http://www.djangoproject.com
.. _django-cbv: http://pypi.python.org/pypi/django-cbv
.. _argparse: http://pypi.python.org/pypi/argparse
