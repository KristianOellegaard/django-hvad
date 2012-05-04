#########################################
Welcome to the Django hvad documentation!
#########################################

.. warning:: Please note that django-hvad is still in alpha status and should be
             used with caution.

.. note:: django-hvad is closely related to (and derives from) django-nani.
           Don't be confused if that name is used in the docs or elsewhere,
           many of the functions are also compatible with django-nani.

******************
About this project
******************

django-hvad provides a high level API to maintain multilingual content in your
database using the Django ORM.

*************************
Before you dive into this
*************************

Please note that this documentation assumes that you are very familiar with 
Django and Python, if you are not, please familiarize yourself with those first.

While django-hvad tries to be as simple to use as possible, it's still
recommended that you only use it if you consider yourself to be very strong in
Python and Django.


************************
Notes on django versions
************************

django-hvad is tested on python 2.6 and 2.7 with django 1.2.7, 1.3.1 and 1.4. These should all work as expected, but for django 1.2.x you need you need to install django-cbv to use the class based views.


***************
Contents
***************

.. toctree::
    :maxdepth: 2

    public/installation
    public/quickstart
    public/models
    public/queryset
    public/forms
    public/admin
    public/release_notes
    public/contact
    public/contributing
    internal/index

    changelog

    glossary
    

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :ref:`glossary`