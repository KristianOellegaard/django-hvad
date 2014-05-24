.. _forms-public:

#####
Forms
#####

Although Django's :class:`~django.forms.ModelForm` can work with translatable
models, they will only know about untranslatable fields. Don't worry though,
django-hvad's got you covered with the following form types:

- :ref:`TranslatableModelForm <translatablemodelform>` is the translation-enabled
  counterpart to Django's :class:`~django.forms.ModelForm`.
- :ref:`Translatable formsets <translatablemodelformset>` is the
  translation-enabled counterpart to Django's
  :djterm:`model formsets <model-formsets>`, for editing several instances
  at once.
- :ref:`Translatable inline formsets <translatableinlineformset>` is the
  translation-enabled counterpart to Django's
  :djterm:`inline formsets <inline-formsets>`, for editing several instances
  attached to another object.
- :ref:`Translation formsets <translationformset>` allows building a formset of
  all the translations of a single instance for editing them all at once. For
  instance, in a tabbed view.

--------

.. _translatablemodelform:

*********************
TranslatableModelForm
*********************

TranslatableModelForms work like :class:`~django.forms.ModelForm`, but can
display and edit translatable fields as well. There use is very similar,
except the form must subclass :class:`~hvad.forms.TranslatableModelForm` instead of
:class:`~django.forms.ModelForm`::

    class ArticleForm(TranslatableModelForm):
        # language = 'en'       # See below
        class Meta:
            model = Article
            fields = ['pub_date', 'headline', 'content', 'reporter']

Notice the difference from :class:`Django's example <django.forms.ModelForm>`?
There is none but for the parent class. This ``ArticleForm`` will allow editing
of one ``Article`` in one language, correctly introspecting the model to know
which fields are translatable.

The language the form uses is computed this way:

- if the form is given a model instance, it will use the language that instance
  was loaded with.
- if this fails, it will look for a ``language`` attribute set on the form.
- if this fails, it will use the current language, as returned by
  :func:`~django.utils.translation.get_language`. If a request is being
  processed, that will be the language of the request.

In all cases, any ``language_code`` field sent with form data will be ignored.
It is the reponsibility of calling code to ensure the data matches the language
of the form.

All features of Django's form work as usual. Just be careful while overriding
the :meth:`~hvad.forms.TranslatableModelForm.save` or
:meth:`~hvad.forms.TranslatableModelForm._post_clean` methods, as they are
crucial parts for the form to work.

.. _translatablemodelformfactory:

*****************************
TranslatableModelForm factory
*****************************

Similar to Django's :djterm:`ModelForm factory <modelforms-factory>`, hvad
eases the generation of uncustomized forms by providing a factory::

    BookForm = translatable_modelform_factory('en', Book, fields=('author', 'title'))

The translation-aware version works exactly the same way as the original one,
except it takes the language the form should use as an additional argument.

.. _translatablemodelformset:

*************************
TranslatableModel Formset
*************************

Similar to Django's :djterm:`ModelFormset factory <model-formsets>`, hvad
provides a factory to create formsets of translatable models::

    AuthorFormSet = translatable_modelformset_factory('en', Author)

It is also possible to override the queryset, the same way you would do it for
a regular formset. In fact, it is recommended, as the default will not prefetch
translations::

    BookForm = translatable_modelformset_factory(
        'en', Book, fields=('author', 'title'),
        queryset=Book.objects.language().filter(name__startswith='O'),
    )

Using :meth:`~hvad.manager.TranslationManager.language` ensures translations will
be loaded at once, and allows filtering on translated fields.

.. note:: To override the form by passing a ``form=`` argument to the factory,
          the custom form must inherit :class:`~hvad.forms.TranslatableModelForm`.

.. _translatableinlineformset:

********************************
TranslatableModel Inline Formset
********************************

Similar to Django's :djterm:`inline formset factory <inline-formsets>`, hvad
provides a factory to create inline formsets of translatable models::

    BookFormSet = translatable_inlineformset_factory('en', Author, Book)

.. note:: To override the form by passing a ``form=`` argument to the factory,
          the custom form must inherit :class:`~hvad.forms.TranslatableModelForm`.

.. _translationformset:

********************
Translations Formset
********************

Basic usage
===========

The translation formset allows one to edit all translations of an
instance at once: adding new translations, updating and deleting existing ones.
It works mostly like regular :class:`~django.forms.models.BaseInlineFormSet`
except it automatically sets itself up for working with the :term:`Translations Model`
of given :class:`~hvad.models.TranslatableModel`.

.. highlight:: python

Example::

    from django.forms.models import modelform_factory
    from hvad.forms import translationformset_factory
    from myapp.models import MyTranslatableModel

    MyUntranslatableFieldsForm = modelform_factory(MyTranslatableModel)
    MyTranslationsFormSet = translationformset_factory(MyTranslatableModel)

Now, ``MyUntranslatableFieldsForm`` is a regular, Django, translation-unaware
form class, showing only the untranslatable fields of an instance, while
``MyTranslationsFormSet`` is a formset class showing only the translatable
fields of an instance, with one form for each available translation (plus any
additional forms requested with the ``extra`` parameter - see
:func:`~django.forms.models.modelform_factory`).

Custom Translation Form
=======================

As with regular formsets, one may specify a custom form class to use. For instance::

    class MyTranslationForm(ModelForm):
        class Meta:
            fields = ['title', 'content', 'slug']

    MyTranslationFormSet = translationformset_factory(
        MyTranslatableModel, form=MyTranslationForm, extra=1
    )

.. note:: The translations formset will use a ``language_code`` field if defined,
          or create one automatically if none was defined.

One may also specify a custom formset class to use. It must inherit
:class:`~hvad.forms.BaseTranslationFormSet`.

Wrapping it up: editing the whole instance
==========================================

A common requirement, being able to edit the whole instance at once, can be
achieved by combining a regular, translation unaware :class:`~django.forms.ModelForm`
with a translation formset in the same view. It works the way one would expect it to.
The following code samples highlight a few gotchas.

Creating the form and formset for the object::

    FormClass = modelform_factory(MyTranslatableModel)
    TranslationsFormSetClass = translationformset_factory(MyTranslatablemodel)

    self.object = self.get_object()
    form = FormClass(instance=self.object, data=request.POST)
    formset = TranslationsFormSetClass(instance=self.object, data=request.POST)

Checking submitted form validity::

    if form.is_valid() and formset.is_valid():
        form.save(commit=False)
        formset.save()
        self.object.save_m2m()  # only if our model has m2m relationships
        return HttpResponseRedirect('/confirm_edit_success.html')

.. note:: When saving the formset, translations will be recombined with the main
          object, and saved as a whole. This allows custom
          :meth:`~django.db.models.Model.save` defined on the model to be called
          properly and signal handlers to be fed a full instance. For this
          reason, we use ``commit=False`` while saving the form, avoiding a
          useless query.

.. warning:: You must ensure that ``form.instance`` and ``formset.instance``
             reference the same object, so that saving the formset does not
             overwrite the values computed by **form**.

A common way to use this view would be to render the ``form`` on top, with
the ``formset`` below it, using JavaScript to show each translation in a tab.

----------

Next, we will take a look at the :doc:`administration panel <admin>`.
