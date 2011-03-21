######
Models
######


***************
Defining models
***************

Models which have fields that should be translateable have to inherit
:class:`nani.models.TranslateableModel` instead of
:class:`django.db.models.Model`. Their default manager (usually the ``objects``
attribute) must be an instance of :class:`nani.manager.TranslationManager` or a
subclass of that class. Your inner :class:`Meta` class on the model may not
use any translated fields in it's options.

Fields to be translated have to be wrapped in a
:class:`nani.models.TranslatedFields` instance which has to be assigned to an
attribute on your model. That attribute will be the reversed ForeignKey from the
:term:`Translations Model` to your :term:`Shared Model`.

If you want to customize your :term:`Translations Model` using directives on a
inner :class:`Meta` class, you can do so by passing a dictionary holding the
directives as the ``meta`` keyword to :class:`nani.models.TranslatedFields`.

A full example of a model with translations::

    from django.db import models
    from nani.models import TranslateableModel, TranslatedFields
    
    
    class Book(TranslateableModel):
        isbn = models.CharField(max_length=13, unique=True)
        
        translations = TranslatedFields(
            title = models.CharField(max_length=255),
            released = models.DateTimeField(),
            meta={'ordering': ['-released']},
        )


***********
New methods
***********


translate
=========

.. method:: translate(language_code)

    Returns this model instance for the language specified.
    
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
    :meth:`__unicode__`.
    
    .. note:: This method does not perform any database queries.
    
Example usage::

    class MyModel(TranslateableModel):
        translations = TranslatedFields(
            name = models.CharField(max_length=255)
        )
        
        def __unicode__(self):
            return self.safe_translation_getter('name', 'MyMode: %s' % self.pk)


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