##########
Quickstart
##########

***************************
Define a multilingual model
***************************

Defining a multilingual model is very similar to defining a normal Django model,
with the difference that instead of subclassing :class:`django.db.models.Model`
you have to subclass :class:`hvad.models.TranslatableModel` and that all fields
which should be translatable have to be wrapped inside a 
:class:`hvad.models.TranslatedFields`.

Let's write an easy model which describes Django applications with translatable
descriptions and information about who wrote the description::

    from django.db import models
    from hvad.models import TranslatableModel, TranslatedFields
    
    
    class DjangoApplication(TranslatableModel):
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

    >>> hvad = DjangoApplication.objects.create(name='django-hvad', author='Jonas Obrist')
    >>> hvad.name
    'django-hvad'
    >>> hvad.author
    'Jonas Obrist'

Turn the **untranslated** instance into a **translated** instance with the
language ``'en'`` (English)::

    >>> hvad.translate('en')
    <DjangoApplication: django-hvad>

Set some translated fields and save the instance::

    >>> hvad.description = 'A project to do multilingual models in Django'
    >>> hvad.description_author = 'Jonas Obrist'
    >>> hvad.save()

Get the instance again and check that the fields are correct::

    >>> obj = DjangoApplication.objects.language('en').get(name='django-hvad')
    >>> obj.name
    u'django-hvad'
    >>> obj.author
    u'Jonas Obrist'
    >>> obj.description
    u'A project to do multilingual models in Django'
    >>> obj.description_author
    u'Jonas Obrist'

.. note:: I use :meth:`~hvad.manager.TranslationQueryset.language` here because
          I'm in an interactive shell, which is not necessarily in English. In
          your normal views, you can usually omit the language simply writing
          `MyModel.objects.language().get(...)`. This will use
          :func:`~django.utils.translation.get_language`
          to get the language the environment is using at the time of the call.

Let's get all Django applications which have a description written by
``'Jonas Obrist'`` (in English)::

    >>> DjangoApplication.objects.language('en').filter(description_author='Jonas Obrist')
    [<DjangoApplication: django-hvad>]
