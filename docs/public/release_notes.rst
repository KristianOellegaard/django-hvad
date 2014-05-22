#############
Release Notes
#############

.. release 0.5.0

*****************************
0.5.0
*****************************

.. note:: This version is being developed. If you feel like helping, or want the
          very latest feature, you can install it from the `github
          repository`_.

New features:

- New :func:`~hvad.forms.translationformset_factory` and its companion
  :class:`~hvad.forms.BaseTranslationFormSet` allow building a formset to work
  on an instance's translations. Please have at look at its detailed
  :ref:`documentation <translationformset>`.
- Django 1.6+'s new :meth:`~django.db.models.query.QuerySet.datetimes` method is
  now available on :class:`~hvad.manager.TranslationQueryset` too.
- Django 1.6+'s new:meth:`~django.db.models.query.QuerySet.earliest` method is
  now available on :class:`~hvad.manager.TranslationQueryset`.
- Calls to :meth:`~hvad.manager.TranslationQueryset.language`, passing `None`
  to use the current language now defers language resolution until the query is
  evaluated. It can now be used in form definitions directly, for instance for
  passing a custom queryset to :class:`~django.forms.ModelChoicefield`.

Deprecation list:

- The deprecated `nani` module was removed.
- Setting `NANI_TABLE_NAME_SEPARATOR` was renamed to `HVAD_TABLE_NAME_SEPARATOR`.
  Using the old name will still work for now, but issue a deprecation warning,
  and get removed in next version.
- CSS class `nani-language-tabs` in admin templates was renamed to
  `hvad-language-tabs`. Entities will bear both classes until next version.

Fixes:

- Method :meth:`~django.db.models.query.QuerySet.latest` now works when passed
  no field name, properly getting the field name from the model's
  `Meta.get_latest_by` option.


.. release 0.4.0

*****************************
0.4.0
*****************************

Released on May 19, 2014

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
- Accessing a translated field on an untranslated instance will now raise an
  :exc:`AttributeError` with a helpful message instead of letting the exception
  bubble up from the ORM.
- Method :meth:`~hvad.manager.TranslationQueryset.in_bulk` is now available on
  :class:`~hvad.manager.TranslationQueryset`.

Deprecation list:

- Catching :exc:`~django.core.exceptions.ObjectDoesNotExist` when accessing
  a translated field on an instance is deprecated. In case no translation
  is loaded and none exists in database for current language, an :exc:`AttributeError`
  is raised instead. For the transition, both are supported until next release.

Removal of the old 'nani' aliases was postponed until next release.

Fixes:

- Fixed an issue where :class:`~hvad.admin.TranslatableAdmin` could overwrite the
  wrong language while saving a form.
- :meth:`~hvad.models.TranslatableModel.lazy_translation_getter` now tries
  translations in `settings.LANGUAGES` order once it has failed with current
  language and site's main `LANGUAGE_CODE`.
- No more deprecation warnings when importing only from :mod:`hvad`.
- :class:`~hvad.admin.TranslatableAdmin` now generates relative URLs instead
    of absolute ones, enabling it to work behind reverse proxies.
- django-hvad does not depend on the default manager being named
    'objects' anymore.
- Q objects now work properly with :class:`~hvad.manager.TranslationQueryset`.

.. release-0.3

*****************************
0.3
*****************************

New Python and Django versions supported:

- django-hvad now supports Django 1.5 running on Python 2.6 and 2.6.

Deprecation list:

. Dropped support for django 1.2.
- In next release, the old 'nani' module will be removed.


.. release-0.2

*****************************
0.2
*****************************

The package is now called 'hvad'. Old imports should result in an import error.

Fixed django 1.4 support

Fixed a number of minor issues



.. release-0.1.4

*****************************
0.1.4 (Alpha)
*****************************

Released on November 29, 2011

 * Introduces :meth:`lazy_translation_getter`


.. release-0.1.3

*****************************
0.1.3 (Alpha)
*****************************

Released on November 8, 2011

 * A new setting was introduced to configure the table name separator, ``NANI_TABLE_NAME_SEPARATOR``.

   .. note::

       If you upgrade from an earlier version, you'll have to rename your tables yourself (the general template is
       ``appname_modelname_translation``) or set ``NANI_TABLE_NAME_SEPARATOR`` to the empty string in your settings (which
       was the implicit default until 0.1.0)

.. release-0.0.4

*****************************
0.0.4 (Alpha)
*****************************

.. release-0.0.3

*************
0.0.3 (Alpha)
*************

Released on May 26, 2011.

* Replaced our ghetto fallback querying code with a simplified version of the
  logic used in Bert Constantins `django-polymorphic`_, all credit for our now
  better FallbackQueryset code goes to him.
* Replaced all JSON fixtures for testing with Python fixtures, to keep tests
  maintainable.
* Nicer language tabs in admin thanks to the amazing help of Angelo Dini.
* Ability to delete translations from the admin.
* Changed hvad.admin.TranslatableAdmin.get_language_tabs signature.
* Removed tests from egg.
* Fixed some tests possibly leaking client state information.
* Fixed a critical bug in hvad.forms.TranslatableModelForm where attempting to
  save a translated model with a relation (FK) would cause IntegrityErrors when
  it's a new instance.
* Fixed a critical bug in hvad.models.TranslatableModelBase where certain field
  types on models would break the metaclass. (Many thanks to Kristian
  Oellegaard for the fix)
* Fixed a bug that prevented abstract TranslatableModel subclasses with no
  translated fields.


.. release-0.0.2

*************
0.0.2 (Alpha)
*************

Released on May 16, 2011.

* Removed language code field from admin.
* Fixed admin 'forgetting' selected language when editing an instance in another
  language than the UI language in admin.


.. release-0.0.1

*************
0.0.1 (Alpha)
*************

Released on May 13, 2011.

* First release, for testing purposes only.


.. _django-polymorphic: https://github.com/bconstantin/django_polymorphic
.. _github repository: https://github.com/KristianOellegaard/django-hvad
