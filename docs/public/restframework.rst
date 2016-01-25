.. _restframework-public:

##############
REST Framework
##############

.. versionadded:: 1.2

What would be a modern application without dynamic components? Well, it would not
be so modern to begin with. This is why django-hvad provides fully tested and integrated
support for `Django REST framework`_.

The philosophy is the same one that is used for Django's :doc:`forms <forms>`,
hvad providing the following extensions:

- :ref:`TranslatableModelSerializer` is the
  translation-enabled counterpart to `ModelSerializer`_.
- :ref:`HyperlinkedTranslatableModelSerializer` is the
  translation-enabled counterpart to `HyperlinkedModelSerializer`_.
- :ref:`TranslationsMixin` can be plugged into a `ModelSerializer` to add a
  dictionary of all available translations. Writing is supported as well.

.. note:: Support for REST framework requires Django REST Framework version 3.1
          or newer.

--------

.. _TranslatableModelSerializer:

***************************
TranslatableModelSerializer
***************************

``hvad.contrib.restframework.TranslatableModelSerializer``

TranslatableModelSerializer works like `ModelSerializer`_, but can
serialize and deserialize translatable fields as well. Their use is very similar,
except the serializer must subclass
:class:`hvad.contrib.restframework.TranslatableModelSerializer`::

    class BookSerializer(TranslatableModelSerializer):
        class Meta:
            model = Book
            fields = ['title', 'author', 'review']

Notice the difference from a regular serializer? There is none. This
``BookSerializer`` will allow serializing and deserializing one ``Book`` in one
language, correctly introspecting the model to know which fields are translatable.

It is also possible to include the language on the serializer. This is done by
default (if no ``fields`` is specified), or you may include ``'language_code'``
as part of the field list.

Like :ref:`TranslatableModelForm <translatablemodelform>`,
``TranslatableModelSerializer`` can work in either normal mode, or **enforce** mode.
The semantics of both mode are exactly the same as with forms, selecting the way
a language is chosen for serializing and deserializing.

* A serializer is in normal mode if it has no language set. This is the default. In
  this mode, it will use the language of the ``instance`` it is given, defaulting
  to current language if no ``instance`` is specified.
* A serializer is in **enforce** mode if is has a language set. This is achieved
  by giving it a ``language=`` argument at instanciation.
  When in **enforce** mode, the serializer will always use its own language, disregarding
  current language and reloading the ``instance`` it is given if it has another
  language loaded.
* The language can be overriden manually by providing a custom ``validate()``
  method. This method should set the desired language in ``data['language_code']``.
  Please refer to REST framework
  `documentation <http://www.django-rest-framework.org/api-guide/serializers/#validation>`_
  for details on the ``validate()`` method.

When the serializer is in normal mode, it is possible to send ``'language_code'``
as part of the serialized representation. More on this below. In **enforce** mode
however, including a language code in a POST, PATCH or PUT request is an error that
will raise a ``ValidationError`` as appropriate.

All features of regular REST framework serializers work as usual.

Examples
--------

Adding the language to the serialized data, in **normal** mode::

    class BookSerializer(TranslatableModelSerializer):
        class Meta:
            model = Book
            fields = ['title', 'author', 'language_code']

    # Now language appears in serialized representation
    serializer = BookSerializer(instance=Book.objects.language('ja').get(pk=1))
    # => {"title": "星の王子さま", "author": "12", "language_code": "ja" }

    # It can also be set explicitly in POST/PUT/PATCH data
    print(data['language_code']) # 'fr'
    serializer = BookSerializer(data=data)
    if serializer.is_valid():
        obj = serializer.save()
        assert obj.language_code == 'fr'

Setting a serializer in **enforce** mode::

    # In enforce mode, serialized data will always use the enforced language
    serializer = BookSerializer(instance=Book.objects.untranslated().get(pk=1), language='en')
    assert serializer.data['language_code'] == 'en'

    # In enforce mode, language is implicit
    assert 'language_code' not in request.data
    serializer = BookSerializer(data=request.data, language='fr')
    if serializer.is_valid():
        obj = serializer.save()
        assert obj.language_code == 'fr'

    # In enforce mode, language must not be provided in data
    assert 'language_code' in request.data
    serializer = BookSerializer(data=request.data, language='fr')
    assert not serializer.is_valid()

Manually overriding deserialized language::

    class UserBookSerializer(TranslatableModelSerializer):
        def validate(self, data):
            # assuming you made a custom User model that has an associated
            # preferences object including the user's preferred language
            data = super(UserBookSerializer, self).validate(data)
            data['language_code'] = self.context['request'].user.preferences.language
            return data

        class Meta:
            model = Book

.. _HyperlinkedTranslatableModelSerializer:

**************************************
HyperlinkedTranslatableModelSerializer
**************************************

``hvad.contrib.restframework.HyperlinkedTranslatableModelSerializer``

The ``HyperlinkedTranslatableModelSerializer`` is equivalent to ``TranslatableModelSerializer``,
except it outputs hyperlinks instead of ids. There is not much to add here,
everything that applies to `TranslatableModelSerializer`_ also applies to
``HyperlinkedTranslatableModelSerializer``, except it uses REST framework's
`HyperlinkedModelSerializer`_ semantics.

--------

.. _TranslationsMixin:

*****************
TranslationsMixin
*****************

``hvad.contrib.restframework.TranslationsMixin``

This mixin is another approach to handling translations for your REST api. With
:ref:`TranslatableModelSerializer`, a relevant language is made visible, which
is perfect for translation-unaware client-side applications. ``TranslationsMixin``
takes the other approach: it exposes all translations at once, letting the
client-side application choose or handle translations the way it wants. This is
most useful for admin-type applications.

Use is very simple: mix it into a regular serializer::

    from rest_framework.serializers import ModelSerializer

    class BookSerializer(TranslationsMixin, ModelSerializer):
        class Meta:
            model = Book

    obj = Book.objects.untranslated().prefetch_related('translations').get(pk=1)
    serializer = BookSerializer(instance=obj)
    pprint(serializer.data)
    # {'author': '1',
    #  'id': 1,
    #  'translations': {'en': {'title': 'The Little Prince'},
    #                   'fr': {'title': 'Le Petit Prince'}}}

.. note:: For performance, you should always prefetch the translations like in
          the above example, otherwise the serializer will have to fetch them
          for each object independently, resulting in a large number of queries.

Writing is supported as well. It takes a dictionary of translations, the very same
format it outputs. Existing translations will be updated, missing translations
will be created. Any existing translation that is not in the data will be deleted.

For convenience, you can include both the translations dictionary and translated
fields in the same serializer. This can be handy if only some parts of your
application care about all the translations. For instance, a book listing might
just want the title in the preferred language, while the book editing dialog
allows editing all languages.
In this case, direct translated fields will be read-only, use the translations
dictionary for updating.

It is possible to override the representation of translations. This is done by
specifying a custom serializer on the meta::

    from rest_framework import serializers

    class BookTranslationSerializer(serializers.ModelSerializer):
        class Meta:
            exclude = ['subtitle', 'cover']

    class BookSerializer(TranslationsMixin, serializers.ModelSerializer):
        class Meta:
            model = Book
            translations_serializer = BookTranslationSerializer

In case advanced customisation of translations is required, be aware that your
custom translation serializer is handed the full object. This allows building
computed fields using both translated and untranslated data.

However, it can interfer with some field types, most notable related fields,
which expect the actual translation model. Hvad handles this automatically in its
default translation serializer. You can inherit this handling by making your own
translation serializer a subclass of ``hvad.contrib.restframework.NestedTranslationSerializer``.

.. _Django REST framework: http://www.django-rest-framework.org/
.. _ModelSerializer: http://www.django-rest-framework.org/api-guide/serializers/#modelserializer
.. _HyperlinkedModelSerializer: http://www.django-rest-framework.org/api-guide/serializers/#hyperlinkedmodelserializer
