============
django-hvad
============

This project is yet another attempt at making model translations suck less in
Django. It uses an automatically created `Translations Model` to store
translatable fields in arbitrary languages with a foreign key to the main model.

Documentation for django-hvad can be found at http://django-hvad.readthedocs.org/.

This project replaces the obsolete django-nani package. It provides the same
functionality, but does not affect the default queries: translated fields have
to be activated by calling a specific method on the `TranslationManager`.

.. warning:: django-hvad is still in beta, please use it with
             caution and report any bug you might encounter on
             https://github.com/KristianOellegaard/django-hvad/issues

**Feel free to join us at #django-hvad on irc.freenode.net for a chat**

.. image:: https://secure.travis-ci.org/KristianOellegaard/django-hvad.png?branch=master


Example
-------

             Normal.objects.all()

Returns all objects, but without any translated fields attached - this query is
just the default django queryset and can therefore be used as usual.

             Normal.objects.language().all()

Returns all objects as translated instances, but only the ones that are translated
into the currect language. You can also specify which language to get, using e.g.

             Normal.objects.language("en").all()


Features
--------

* Simple API 
* Predictable
* Reliable
* Versatile (can manipulate arbitrary languages without changing the DB layout)
* Fast (few and simple queries)
* High level (no custom SQL Compiler or other scary things)


Thanks to
---------

Jonas Obrist (https://github.com/ojii) for making django-nani and for helping me with this project.
