##########
Quickstart
##########

***************************
Define a multilingual model
***************************

Defining a multilingual model is very similar to defining a normal Django model,
with the difference that instead of subclassing :class:`~django.db.models.Model`
you have to subclass :class:`~hvad.models.TranslatableModel` and that all fields
which should be translatable have to be wrapped inside a 
:class:`~hvad.models.TranslatedFields`.

Let's write an easy model which describes Django applications with translatable
descriptions and information about who wrote the description::

    from django.db import models
    from hvad.models import TranslatableModel, TranslatedFields
    
    
    class DjangoApplication(TranslatableModel):
        name = models.CharField(max_length=255, unique=True)
        author = models.CharField(max_length=255)
        
        translations = TranslatedFields(
            description=models.TextField(),
            description_author=models.CharField(max_length=255),
        )
        
        def __str__(self):
            return self.name

The fields ``name`` and ``author`` will not get translated, the fields
``description`` and ``description_author`` will.

.. note:: To use a translated field in the ``__str__`` method,
          please read :ref:`this FAQ entry <translatable-str>`.

****************************
Create a translated instance
****************************

Now that we have defined our model, let's play around with it a bit. The
following code examples are taken from a Python shell.

.. highlight:: pycon

Import our model::

    >>> from myapp.models import DjangoApplication

Create an instance::

    >>> hvad = DjangoApplication.objects.language('en').create(
        name='django-hvad', author='Jonas Obrist',
        description='A project to do multilingual models in Django',
        description_author='Jonas Obrist',
    )
    >>> hvad.name
    'django-hvad'
    >>> hvad.author
    'Jonas Obrist'
    >>> hvad.description
    'A project to do multilingual models in Django'
    >>> hvad.description_author
    'Jonas Obrist'
    >>> hvad.language_code
    'en'
    >>> hvad.save()

This is the most straightforward way to create a new instance with translated
fields. Doing it this way avoids the possibility of creating instances with
no translation at all, which would be an error.

Once we have an instance, we can add new translations. Let's add some French::

    >>> hvad.translate('fr')
    <DjangoApplication: django-hvad>
    >>> hvad.name
    'django-hvad'
    >>> hvad.description
    >>> hvad.language_code
    'fr'
    >>> hvad.description = 'Un projet pour gérer des modèles multilingues sous Django'
    >>> hvad.description_author = 'Julien Hartmann'
    >>> hvad.save()

.. note:: The :meth:`~hvad.models.TranslatableModel.translate` method creates a
          brand new translation in the specified language. Please note
          that it does not check the database, and that if the translation
          already exists, a database integrity exception will be raised when saving.

****************************
Querying translatable models
****************************

Get the instance again and check that the fields are correct::

    >>> obj = DjangoApplication.objects.language('en').get(name='django-hvad')
    >>> obj.name
    'django-hvad'
    >>> obj.author
    'Jonas Obrist'
    >>> obj.description
    'A project to do multilingual models in Django'
    >>> obj.description_author
    'Jonas Obrist'
    >>> obj.language_code
    'en'

We use :meth:`~hvad.manager.TranslationManager.language` to tell hvad we want
to use translated fields, in English. This is one of the three ways to query
a translatable model. It only ever considers instances that have a translation in
the specified language and match the filters in that language.

Second way is to add a call to :meth:`~hvad.manager.TranslationManager.fallbacks`
after ``language()``, enabling a fallback algorithm to fetch the best translation
within a list of languages.

Lastly, :meth:`~hvad.manager.TranslationManager.untranslated`, allows a direct,
vanilla use of the queryset, which does not know about translations or translated
fields at all.

If neither ``language()`` nor ``untranslated()`` is used, one is picked
automatically depending on :ref:`USE_DEFAULT_QUERYSET <settings>` setting.

Back to our instance, get it again, in other languages::

    >>> obj = DjangoApplication.objects.language('fr').get(name='django-hvad')
    >>> obj.description
    'Un projet pour gérer des modèles multilingues sous Django'
    >>> obj.language_code
    'fr'

    >>> DjangoApplication.objects.language('ja').filter(name='django-hvad')
    []

See how, in the second query, the fact that no translation exist in Japanese for
our object had it filtered out of the query.

.. note:: We set an explicit language when calling
          :meth:`~hvad.manager.TranslationQueryset.language` because
          we are in an interactive shell.
          In your normal views, you can usually omit the language simply writing
          ``MyModel.objects.language().get(...)``. This will use
          :func:`~django.utils.translation.get_language`
          to get the language the environment is using at the time of the query.
          This requires the LocaleMiddleware is :ref:`properly setup <localemiddleware>`.

Let's get all Django applications which have a description written by
``'Jonas Obrist'`` (in English, then in French)::

    >>> DjangoApplication.objects.language('en').filter(description_author='Jonas Obrist')
    [<DjangoApplication: django-hvad>]
    >>> DjangoApplication.objects.language('fr').filter(description_author='Jonas Obrist')
    []

Notice how the second query only considers French translations and returns an empty set.

----------

Next, we will have a more detailed look at how to :doc:`work with translatable models <models>`.
