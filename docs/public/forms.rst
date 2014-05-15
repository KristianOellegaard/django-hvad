.. _forms-public:

#####
Forms
#####

*********************
TranslatableModelForm
*********************

If you want to use your :term:`Translated Model` in forms, you
have to subclass :class:`hvad.forms.TranslatableModelForm` instead of
:class:`django.forms.ModelForm`.

Please be careful while overriding the :meth:`~hvad.forms.TranslatableModelForm.save`
or :meth:`~hvad.forms.TranslatableModelForm._post_clean` methods, as they are crucial
parts for the form to work.

********************
Translations Formset
********************

Basic usage
===========

The translation formset allows one to edit all translations of an
instance at once: adding new translations, updating and deleting existing ones.
It works mostly like regular :class:`~django.forms.formsets.BaseInlineFormSet`
except it automatically sets itself up for working with the :term:`Translations Model`
of given :class:`~hvad.models.TranslatableModel`.

.. highlight:: python

Example::

    from django.forms.models import modelform_factory
    from hvad.forms import translationformset_factory
    from myapp.models import MyTranslatableModel

    MyUntranslatableFieldsForm = modelform_factory(MyTranslatableModel)
    MyTranslationsFormSet = translationformset_factory(MyTranslatableModel)

Now, **MyUntranslatableFieldsForm** is a regular, Django, translation-unaware
form class, showing only the untranslatable fields of an instance, while
**MyTranslationsFormSet** is a formset class showing only the translatable
fields of an instance, with one form for each available translation (plus any
additional forms requested with the **extra** parameter - see
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

.. note:: The translations formset will use a **language_code** field if defined,
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
          reason, we use `commit=False` while saving the form, avoiding a
          useless query.

.. warning:: You must ensure that **form.instance** and **formset.instance**
             reference the same object, so that saving the formset does not
             overwrite the values computed by **form**.

A common way to use this view would be to render the **form** on top, with
the **formset** below it, using JavaScript to show each translation in a tab.
