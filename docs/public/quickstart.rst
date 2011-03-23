##########
Quickstart
##########

***************************
Define a multilingual model
***************************

Defining a multilingual model is very similar to defining a normal Django model,
with the difference that instead of subclassing :class:`django.db.models.Model`
you have to subclass :class:`nani.models.TranslateableModel` and that all fields
which should be translateable have to be wrapped inside a 
:class:`nani.models.TranslatedFields`.

Let's write an easy model which describes Django applications with translateable
descriptions and information about who wrote the description::

    from django.db import models
    from nani.models import TranslateableModel, TranslatedFields
    
    
    class DjangoApplication(TranslateableModel):
        name = models.CharField(max_length=255, unique=True)
        author = models.CharField(max_length=255)
        
        translations = TranslatedFields(
            description = models.TextField(),
            description_author = models.CharField(max_length=255),
        )
        
        def __unicode__(self):
            return self.name

The fields ``name`` and ``author`` will not get translated, the fields
``description`` and ``description_author`` will.


*************************
Using multilingual models
*************************

Now that we have defined our model, let's play around with it a bit. The
following code examples are taken from a Python shell.

.. highlight:: pycon

Import our model::

    >>> from myapp.models import DjangoApplication

Create an **untranslated** instance::

    >>> nani = DjangoApplication.objects.create(name='project-nani', author='Jonas Obrist')
    >>> nani.name
    'project-nani'
    >>> nani.author
    'Jonas Obrist'

Turn the **untranslated** instance into a **translated** instance with the
language ``'en'`` (English)::

    >>> nani.translate('en')
    <DjangoApplication: project-nani>

Set some translated fields and save the instance::

    >>> nani.description = 'A project do do multilingual models in Django'
    >>> nani.description_author = 'Jonas Obrist'
    >>> nani.save()

Get the instance again and check that the fields are correct. Please note the
usage of :meth:`nani.manager.TranslationManager.language` here::

    >>> obj = DjangoApplication.objects.language('en').get(name='project-nani')
    >>> obj.name
    u'project-nani'
    >>> obj.author
    u'Jonas Obrist'
    >>> obj.description
    u'A project do do multilingual models in Django'
    >>> obj.description_author
    u'Jonas Obrist'

Let's get all Django applications which have a description written by
``'Jonas Obrist'``::

    >>> DjangoApplication.objects.filter(description_author='Jonas Obrist')
    [<DjangoApplication: project-nani>]