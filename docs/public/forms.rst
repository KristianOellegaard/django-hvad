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
display and edit translatable fields as well. Their use is very similar,
except the form must subclass :class:`~hvad.forms.TranslatableModelForm` instead of
:class:`~django.forms.ModelForm`::

    class ArticleForm(TranslatableModelForm):
        class Meta:
            model = Article
            fields = ['pub_date', 'headline', 'content', 'reporter']

Notice the difference from :class:`Django's example <django.forms.ModelForm>`?
There is none but for the parent class. This ``ArticleForm`` will allow editing
of one ``Article`` in one language, correctly introspecting the model to know
which fields are translatable.

The form can work in either normal mode, or **enforce** mode. This affects the
way the form chooses a language for displaying and committing.

* A form is in normal mode if it has no language set. This is the default. In
  this mode, it will use the language of the ``instance`` it is given, defaulting
  to current language if not ``instance`` is specified.
* A form is in **enforce** mode if is has a language set. This is usually achieved
  by calling :ref:`translatable_modelform_factory <translatablemodelformfactory>`.
  When in **enforce** mode, the form will always use its language, disregarding
  current language and reloading the ``instance`` it is given if it has another
  language loaded.
* The language can be overriden manually by providing a
  :meth:`custom clean() method <django.forms.Form.clean>`.

In all cases, the language is not part of the form seen by the browser or sent
in the POST request. If you need to change the language based on some user
input, you must override the ``clean()`` method with your own logic, and set
:attr:`~django.forms.Form.cleaned_data` ``['language_code']`` with it.

All features of Django forms work as usual.

.. _translatablemodelformfactory:

*****************************
TranslatableModelForm factory
*****************************

Similar to Django's :djterm:`ModelForm factory <modelforms-factory>`, hvad
eases the generation of uncustomized forms by providing a factory::

    BookForm = translatable_modelform_factory('en', Book, fields=('author', 'title'))

The translation-aware version works exactly the same way as the original one,
except it takes the language the form should use as an additional argument.

The returned form class is in **enforce** mode.

.. note:: If using the ``form=`` parameter, the given form class must inherit
          :ref:`TranslatableModelForm <translatablemodelform>`.

.. _translatablemodelformset:

*************************
TranslatableModel Formset
*************************

Similar to Django's :djterm:`ModelFormset factory <model-formsets>`, hvad
provides a factory to create formsets of translatable models::

    AuthorFormSet = translatable_modelformset_factory('en', Author)

This formset allows edition a collection of ``Author`` instances, all of them
being in English.

All arguments supported by Django's :func:`~django.forms.models.modelformset_factory`
can be used.

For instance, it is possible to override the queryset, the same way it is done for
a regular formset. In fact, it is recommended for performance, as the default
queryset will not prefetch translations::

    BookForm = translatable_modelformset_factory(
        'en', Book, fields=('author', 'title'),
        queryset=Book.objects.language('en').all(),
    )

Here, using :meth:`~hvad.manager.TranslationManager.language` ensures translations
will be loaded at once, and allows filtering on translated fields is needed.

The returned formset class is in **enforce** mode.

.. note:: To override the form by passing a ``form=`` argument to the factory,
          the custom form must inherit :ref:`TranslatableModelForm <translatablemodelform>`.

.. _translatableinlineformset:

********************************
TranslatableModel Inline Formset
********************************

Similar to Django's :djterm:`inline formset factory <inline-formsets>`, hvad
provides a factory to create inline formsets of translatable models::

    BookFormSet = translatable_inlineformset_factory('en', Author, Book)

This creates an inline formset, allowing edition of a collection of instances of
``Book`` attached to a single instance of ``Author``, all of those objects
being editted in English. It does not allow editting other languages; for this,
please see :ref:`translationformset_factory <translationformset>`.

Any argument accepted by Django's :func:`~django.forms.models.inlineformset_factory`
can be used with ``translatable_inlineformset_factory`` as well.

The returned formset class is in **enforce** mode.

.. note:: To override the form by passing a ``form=`` argument to the factory,
          the custom form must inherit :ref:`TranslatableModelForm <translatablemodelform>`.

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
