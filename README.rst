============
django-hvad |build|
============
**Model translations made easy.**

*This project replaces the obsolete django-nani package.*

This is yet another project to make model translations suck less in
Django. It uses an automatically created `Translations Model` to store
translatable fields in arbitrary languages with a foreign key to the main model.

- **Documentation** can be found at http://django-hvad.readthedocs.org/.
- **Release notes** can be found at https://django-hvad.readthedocs.org/en/latest/public/release_notes.html.
- **Support** can be found on https://github.com/KristianOellegaard/django-hvad/issues.

Feel free to join us at #django-hvad on irc.freenode.net for a chat

Features
--------

* **Simple API** - less than 10 new methods.
* **Reliable** - more than 200 test cases and counting. |build|
* **Versatile** - can manipulate arbitrary languages without changing the DB schema.
* **Complete** - supports relationships, proxy models, and - from v0.5 - abstract models.
* **Fast** - few and simple queries
* **High level** - no custom SQL Compiler or other scary things
* **Batteries included** - translation-enabled forms and admin are provided.
* **Compatible** with Django 1.3 to 1.7, running Python 2.6+ or 3.3+.

**Warning**

Although we focus on keeping the code stable and clean even on the development
branch, django-hvad is still in beta. Please use it with caution and report any
bug you might encounter on the `issue tracker`_. If stability is
critical, stick to `packaged releases`_ and explicitly prevent automatic
upgrades to next branch (e.g. put ``django-hvad>=0.4,<0.5`` in your requirements).


Releases
--------

Starting from v0.4, django-hvad uses the same release pattern as Django. The
following versions are thus available:

* Stable branch 0.4, available through `PyPI`_ and git branch ``releases/0.4.x``.
* Development branch 0.5, available through git branch ``master``.

See the `installation guide`_ for details, or have a look at the
`release notes`_.

Example Use
-----------

             Books.objects.all()

Returns all objects, but without any translated fields attached - this query is
just the default django queryset and can therefore be used as usual.

             Books.objects.language().all()

Returns all objects as translated instances, but only the ones that are translated
into the currect language. You can also specify which language to get, using e.g.

             Books.objects.language("en").all()

Usual queryset methods work as usual: let's get all books as translated instances,
filtering on the translatable ``title`` attribute, returning those that have
``Petit Prince`` in their French title, ordered by publication date (in their
French edition):

             Books.objects.language("fr").filter(title__contains='Petit Prince').order_by('publish_date')

More examples in the `quickstart guide`_.

Thanks to
---------

Jonas Obrist (https://github.com/ojii) for making django-nani and for helping me with this project.

.. |build| image:: https://secure.travis-ci.org/KristianOellegaard/django-hvad.png?branch=master
.. _PyPI: https://pypi.python.org/pypi/django-hvad
.. _packaged releases: https://pypi.python.org/pypi/django-hvad
.. _installation guide: http://django-hvad.readthedocs.org/en/latest/public/installation.html
.. _release notes: https://django-hvad.readthedocs.org/en/latest/public/release_notes.html
.. _quickstart guide: http://django-hvad.readthedocs.org/en/latest/public/quickstart.html
.. _issue tracker: https://github.com/KristianOellegaard/django-hvad/issues
