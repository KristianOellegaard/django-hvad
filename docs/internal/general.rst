#############################################
General information on django-hvad internals
#############################################


************
How it works
************


Model Definition
================

Function :func:`hvad.models.prepare_translatable_model` is invoked by Django
metaclass using :data:`~django.db.models.signals.class_prepared` signal. It
scans all attributes on the model defined for instances of
:class:`hvad.models.TranslatedFields`, and if it finds one, sets the respective
options onto meta.

:class:`~hvad.models.TranslatedFields` both creates the
:term:`Translations Model` and makes a foreign key from that model to point to
the :term:`Shared Model` which has the name of the attribute of the
:class:`~hvad.models.TranslatedFields` instance as related name.

In the database, two tables are created:

* The table for the :term:`Shared Model` with the normal Django way of defining
  the table name.
* The table for the :term:`Translations Model`, which if not specified otherwise
  in the options (meta) of the :term:`Translations Model` will have the name of
  the database table of the :term:`Shared Model` suffixed by ``_translations``
  as database table name.


Queries
=======

The main idea of django-hvad is that when you query the :term:`Shared Model`
using the Django ORM, what actually happens behind the scenes (in the queryset)
is that it queries the :term:`Translations Model` and selects the relation to
the :term:`Shared Model`. This means that model instances can only be queried if
they have a translation in the language queried in, unless an alternative 
manager is used, for example by using
:meth:`~hvad.manager.TranslationManager.untranslated`.

Due to the way the Django ORM works, this approach does not seem to be possible
when querying from a :term:`Normal Model`, even when using 
:func:`hvad.utils.get_translation_aware_manager` and therefore in that case we
just add extra filters to limit the lookups to rows in the database where the
:term:`Translations Model` row existist in a specific language, using
``<translations_accessor>__language_code=<current_language>``. This is
suboptimal since it means that we use two different ways to query translations
and should be changed if possible to use the same technique like when a
:term:`Translated Model` is queried. 


*****************
A word on caching
*****************

Throughout this documentation, caching of translations is mentioned a lot. By
this we don't mean proper caching using the Django cache framework, but rather
caching the instance of the :term:`Translations Model` on the instance of the
:term:`Shared Model` for easier access. This is done by setting the instance of 
the :term:`Translations Model` on the attribute defined by the
:attr:`~hvad.models.TranslatableModel.translations_cache` on the :term:`Shared Model`'s options (meta).
