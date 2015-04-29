#################
How to contribute
#################


*****************
Running the tests
*****************

Common Setup
============

* ``virtualenv env``
* ``source env/bin/activate``
* ``pip install django sphinx djangorestframework``

Postgres Setup
==============

Additional to the steps above, install ``psycopg2`` using pip and have a
postgres server running that you have access to with a user that can create
databases.

Mysql Setup
===========

Additional to the steps above, install ``mysql-python`` using pip and have a
mysql server running that you have access to with a user that can create
databases.

Run the test
============

* ``python runtests.py``

Optionally, prefix it with a environment variable called ``DATBASE_URL``, for
example for a Postgres server running on ``myserver.com`` on port ``5432``
with the user ``username`` and password ``password`` and database name ``hvad``:

* ``DATABASE_URL=postgres://username:password@myserver.com:5432/hvad python runtests.py``

If in doubt, you can check ``.travis.yml`` for some examples.

*****************
Contributing Code
*****************

If you want to contribute code, one of the first things you should do is read
the :doc:`/internal/index`. It was written for developers who want to
understand how things work.

Patches can be sent as pull requests on Github to
https://github.com/KristianOellegaard/django-hvad.


Code Style
==========

The :pep:`8` coding guidelines should be followed when contributing code to this
project. 

Patches **must** include unittests that fully cover the changes in the patch.

Patches **must** contain the necessary changes or additions to both the
*internal* and *public* documentation.

If you need help with any of the above, feel free to :doc:`contact` us.


**************************
Contributing Documentation
**************************

If you wish to contribute documentation, be it for fixes of typos and grammar or
to cover the code you've written for your patch, or just generally improve our
documentation, please follow the following style guidelines:

* Documentation is written using `reStructuredText`_ and `Sphinx`_.
* Text should be wrapped at 80 characters per line. Only exception are over-long
  URLs that cannot fit on one line and code samples.
* The language does not have to be perfect, but please give your best.
* For section headlines, please use the following style:

    * ``#`` with overline, for parts
    * ``*`` with overline, for chapters
    * ``=``, for sections
    * ``-``, for subsections
    * ``^``, for subsubsections
    * ``"``, for paragraphs

.. _RestructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://sphinx.pocoo.org
