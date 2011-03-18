######
Models
######

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