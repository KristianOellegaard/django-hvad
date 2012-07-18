########################
:mod:`hvad.compat.date`
########################

.. module:: hvad.compat.date

This module provides backwards compatiblity for Django 1.2 for the
:meth:`django.db.models.query.QuerySet.dates` API, which in Django 1.3 allows
the fieldname to span relations.


************
DateQuerySet
************

.. class:: DateQuerySet

    Backport of :class:`django.db.models.query.DateQuerySet` from Django 1.3.
    

*********
DateQuery
*********

.. class:: DateQuery

    Backport of :class:`django.db.models.sql.subqueries.DateQuery` from Django
    1.3.