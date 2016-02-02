========================================
django-hvad |package| |coverage| |build|
========================================

**Model translations made easy.**

This project adds support for model translations in Django. It is designed to be
unobtrusive, efficient and reliable. On the technical side, it uses an automatically
created `Translations Model` to store translatable fields in arbitrary
languages with a foreign key to the main model, enabling fast queries.

Started in 2011, hvad has grown mature and is now used on large scale applications.

Quick links:

- `Documentation`_.
- `Release notes`_.
- `Issue tracker`_.

Features
--------

* **Simple** - only 3 new queryset methods.
* **Natural** - use Django ORM as usual, it just became language aware.
* **Fast** - no additional queries for reads, just an inner join to an indexed key.
* **Complete** - relationships, custom managers and querysets, proxy models, and abstract models.
* **Batteries included** - translation-enabled forms and admin are provided.
* **Reliable** - more than 300 test cases and counting. |coverage| |build|
* **Compatible** with Django 1.4 to 1.9, running Python 2.7, 3.3, 3.4 or 3.5.

Django-hvad also features support for `Django REST framework`_ 3.1 or newer, including
translation-aware serializers.

Example Uses
------------

Declaring a translatable ``Book`` model::

    class Book(TranslatableModel):
        author = models.ForeignKey(Author)
        release = models.Date()

        translations = TranslatedFields(
            title = models.CharField(max_length=250)
        )

Thus, only the title will vary based on the language. Release date and
author are shared among all languages. Let's now create a ``Book`` instance::

    # The recommended way:
    book = Book.objects.language('en').create(
        author = Author.objects.get(name='Antoine de Saint Exupéry'),
        release = datetime.date(1943, 4, 6),
        title = "The Little Prince",
    )

    # Also works
    book = Book(language_code='en')
    book.author = Author.objects.get(name='Antoine de Saint Exupéry')
    book.release = datetime.date(1943, 4, 6)
    book.title = "The Little Prince"
    book.save()

Providing some translations::

    book.translate('fr')
    book.title = "Le Petit Prince"
    book.save()
    book.translate('de')
    book.title = "Der kleine Prinz"
    book.save()

Every call to ``translate()`` creates a new translation from scratch and switches
to that translation; ``save()`` only saves the latest translation. Let's now perform
some language-aware queries::

    Book.objects.all()

Compatible by default: returns all objects, without any translated fields attached.
Starting from v1.0, default behavior can be overriden to work like next query::

    Book.objects.language().all()

Returns all objects as translated instances, but only the ones that are translated
into the currect language. You can also specify which language to get, using e.g.::

    Book.objects.language("en").all()

Usual queryset methods work like they always did: let's get all books as translated instances,
filtering on the ``title`` attribute, returning those that have
``Petit Prince`` in their French title, ordered by publication date (in their
French edition)::

    Book.objects.language("fr").filter(title__contains='Petit Prince').order_by('release')

Other random examples::

    # last German book published in year 1948
    Book.objects.language("de").filter(release__year=1948).latest()

    # other books from the same author as mybook. Cache author as well.
    Book.objects.language().select_related('author').filter(author__books=mybook)

    # books that have "Django" in their title, regardless of the language
    Book.objects.language('all').filter(title__icontains='Django')


More examples in the `quickstart guide`_.

Releases
--------

Django-hvad uses the same release pattern as Django. The following versions
are thus available:

* Stable branch 1.4, available through `PyPI`_ and git branch ``releases/1.4.x``.
* Stable branch 1.5, available through `PyPI`_ and git branch ``releases/1.5.x``.
* Development branch 1.6, available through git branch ``master``.

Stable branches have minor bugfix releases as needed, with guaranteed compatibility.
See the `installation guide`_ for details, or have a look at the `release notes`_.

Thanks to
---------

Jonas Obrist (https://github.com/ojii) for making django-nani and for helping me with this project.

Kristian Øllegaard (https://github.com/KristianOellegaard/) for django-hvad and trusting me
to continue the development.

.. |package| image:: https://badge.fury.io/py/django-hvad.svg
                     :target: https://pypi.python.org/pypi/django-hvad
.. |build| image:: https://secure.travis-ci.org/KristianOellegaard/django-hvad.png?branch=master
.. |coverage| image:: https://coveralls.io/repos/KristianOellegaard/django-hvad/badge.png
                      :target: https://coveralls.io/r/KristianOellegaard/django-hvad

.. _documentation: http://django-hvad.readthedocs.org/
.. _release notes: https://django-hvad.readthedocs.org/en/latest/public/release_notes.html
.. _issue tracker: https://github.com/KristianOellegaard/django-hvad/issues
.. _PyPI: https://pypi.python.org/pypi/django-hvad
.. _Django REST framework: http://www.django-rest-framework.org/
.. _installation guide: http://django-hvad.readthedocs.org/en/latest/public/installation.html
.. _quickstart guide: http://django-hvad.readthedocs.org/en/latest/public/quickstart.html

