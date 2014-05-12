######
Models
######


***************
Defining models
***************

Models which have fields that should be translatable have to inherit
:class:`hvad.models.TranslatableModel` instead of
:class:`django.db.models.Model`. Their default manager (usually the ``objects``
attribute) must be an instance of :class:`hvad.manager.TranslationManager` or a
subclass of that class. Your inner :class:`Meta` class on the model may not
use any translated fields in it's options.

Fields to be translated have to be wrapped in a
:class:`hvad.models.TranslatedFields` instance which has to be assigned to an
attribute on your model. That attribute will be the reversed ForeignKey from the
:term:`Translations Model` to your :term:`Shared Model`.

If you want to customize your :term:`Translations Model` using directives on a
inner :class:`Meta` class, you can do so by passing a dictionary holding the
directives as the ``meta`` keyword to :class:`~hvad.models.TranslatedFields`.

A full example of a model with translations::

    from django.db import models
    from hvad.models import TranslatableModel, TranslatedFields
    
    
    class TVSeries(TranslatableModel):
        distributor = models.CharField(max_length=255)
        
        translations = TranslatedFields(
            title = models.CharField(max_length=100),
            subtitle = models.CharField(max_length=255),
            released = models.DateTimeField(),
            meta={'unique_together': [('title', 'subtitle')]},
        )


.. note::

    When using proxy models with hvad, the ``__init__`` method of the proxy
    model will not be called when it is loaded from the database. As a result,
    the ``pre_init`` and ``post_init`` signals will not be called for the proxy
    model either. The ``__init__`` method and signals for the concrete model
    will still be called.

***********
New methods
***********


translate
=========

.. method:: translate(language_code)

    Prepares a new translation for this instance for the language specified.
    
    .. warning:: This does **not** check if this language already exists in the
                 database and assumes it doesn't! If it already exists and you
                 try to save this instance, it will break!

    .. note:: This method does not perform any database queries.


safe_translation_getter
=======================

.. method:: safe_translation_getter(name, default=None)

    Returns the value of the field specified by ``name`` if it's available on
    this instance in the currently cached language. It does not try to get the
    value from the database. Returns the value specified in ``default`` if no
    translation was cached on this instance or the translation does not have a
    value for this field.
    
    This method is useful to safely get a value in methods such as
    :meth:`~django.db.models.Model.__unicode__`.
    
    .. note:: This method never performs any database queries.
    
Example usage::

    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            name = models.CharField(max_length=255)
        )
        
        def __unicode__(self):
            return self.safe_translation_getter('name', 'MyMode: %s' % self.pk)
            
            
.. method:: lazy_translation_getter(name, default=None)

    Tries to get the value of the field specified by ``name`` using
    :meth:`safe_translation_getter`. If this fails, tries to load a translation
    from the database. If none exists, returns the value specified in ``default``.

    This method is useful to get a value in methods such as
    :meth:`~django.db.models.Model.__unicode__`.

    .. note:: This method may perform database queries.

Example usage::

    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            name = models.CharField(max_length=255)
        )

        def __unicode__(self):
            return self.lazy_translation_getter('name', 'MyMode: %s' % self.pk)


get_available_languages
=======================

.. method:: get_available_languages

    Returns a list of available language codes for this instance.
    
    .. note:: This method runs a database query to fetch the available
              languages.


***************
Changed methods
***************


save
====

.. method:: save(force_insert=False, force_update=False, using=None)

    This method runs an extra query when used to save the translation cached on
    this instance, if any translation was cached.


**********************
Working with relations
**********************

Foreign keys pointing to a :term:`Translated Model` always point to the
:term:`Shared Model`. It is currently not possible to have a foreign key to a
:term:`Translations Model`.

Please note that :meth:`django.db.models.query.QuerySet.select_related` used on
a foreign key pointing to a :term:`Translated Model` does not span to its
:term:`Translations Model` and therefore accessing a translated field over the
relation causes an extra query.

If you wish to filter over a translated field over the relation from a
:term:`Normal Model` you have to use
:func:`hvad.utils.get_translation_aware_manager` to get a manager that allows
you to do so. That function takes your model class as argument and returns a
manager that works with translated fields on related models.
