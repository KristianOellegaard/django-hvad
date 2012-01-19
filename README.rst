============
django-hvad
============

This project is yet another attempt at making model translations suck less in
Django.

This project provides the same functionality as django-nani, but it as opposed to django-nani, this project does not affect the default queries, which means that everything will continue to work as it was before.

You have to activate the translated fields, by calling a specific method on the manager.

.. warning:: django-hvad is still in beta, please use it with
             caution and report any bug(s) you might encounter.

**Feel free to join us at #django-hvad on irc.freenode.net for a chat**



Example
-------

             Normal.objects.all()

Returns all objects, but without any translated fields attached - this query is just the default django queryset and can therefore be used as usual.

             Normal.objects.language().all()

Returns all objects as translated instances, but only the ones that are translated into the currect language. You can also specify which language to get, using e.g.

             Normal.objects.language("en").all()


Features
--------

* Simple API 
* Predictable
* Reliable
* Fast (few and simple queries)
* High level (no custom SQL Compiler or other scary things)


Important
---------

We keep the nani name internally in the code, as we want to be able to adapt and contribute to/from django-nani

Thanks to
---------

Jonas Obrist (https://github.com/ojii) for making django-nani and for helping me with this project.