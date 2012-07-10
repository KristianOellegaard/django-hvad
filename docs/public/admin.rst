#####
Admin
#####

When you want to use a :term:`Translated Model` in the Django
admin, you have to subclass :class:`nani.admin.TranslatableAdmin` instead of
:class:`django.contrib.admin.ModelAdmin`.


***********
New methods
***********

all_translations
================

.. method:: all_translations(obj)

    A method that can be used in :attr:`list_display` and shows a list of
    languages in which this object is available.


***********************************************************
ModelAdmin APIs you should not change on TranslatableAdmin
***********************************************************

Some public APIs on :class:`django.contrib.admin.ModelAdmin` are crucial for
:class:`nani.admin.TranslatableAdmin` to work and should not be altered in
subclasses. Only do so if you have a good understanding of what the API you want
to change does.

The list of APIs you should not alter is:

change_form_template
====================

If you wish to alter the template to be used to render your admin, use the
implicit template fallback in the Django admin by creating a template named
``admin/<appname>/<modelname>/change_form.html`` or
``admin/<appname>/change_form.html``. The template used in django-nani will
automatically extend that template if it's available.

get_form
========

Use :attr:`nani.admin.TranslatableAdmin.form` instead, but please see the notes
regarding :ref:`admin-forms-public`.

render_change_form
==================

The only thing safe to alter in this method in subclasses is the context, but
make sure you call this method on the superclass too. There's three variable
names in the context you should not alter:

* ``title``
* ``language_tabs``
* ``base_template``

get_object
==========

Just don't try to change this.

queryset
========

If you alter this method, make sure to call it on the superclass too to prevent
duplicate objects to show up in the changelist or change views raising
:exc:`django.core.exceptions.MultipleObjectsReturned` errors.


.. _admin-forms-public:

**************
Forms in admin
**************

If you want to alter the form to be used on your
:class:`nani.admin.TranslatableAdmin` subclass, it must inherit from
:class:`nani.forms.TranslatableModelForm`. For more informations, see
:ref:`forms-public`.


***************************************************
ModelAdmin APIs not available on TranslatableAdmin
***************************************************

A list of public APIs on :class:`django.contrib.admin.ModelAdmin` which are not
implemented on :class:`nani.admin.TranslatableAdmin`. 

* :attr:`list_display` [#f1]_
* :attr:`list_display_links` [#f1]_
* :attr:`list_filter` [#f1]_
* :attr:`list_select_related` [#f1]_
* :attr:`list_ediable` [#f1]_
* :attr:`search_fields` [#f1]_
* :attr:`date_hierarchy` [#f1]_
* :attr:`actions` [#f1]_

.. rubric:: Footnotes

.. [#f1] This API can only be used with :term:`Shared Fields`.
