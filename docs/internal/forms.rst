#################
:mod:`hvad.forms`
#################

.. module:: hvad.forms


*******************************
TranslatableModelFormMetaclass
*******************************

.. class:: TranslatableModelFormMetaclass

    Metaclass of :class:`TranslatableModelForm`.

    .. method:: __new__(cls, name, bases, attrs)
    
        The main thing happening in this metaclass is that the declared and base
        fields on the form are built by calling
        :func:`django.forms.models.fields_for_model` using the correct model
        depending on whether the field is translated or not. This metaclass also
        enforces the translations accessor and the master foreign key to be
        excluded.


**********************
TranslatableModelForm
**********************

.. class:: TranslatableModelForm(ModelForm)

    .. attribute:: __metaclass__
    
        :class:`TranslatableModelFormMetaclass`

    .. method:: __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, initial=None, error_class=ErrorList, label_suffix=':', empty_permitted=False, instance=None)
    
        If this class is initialized with an instance, it updates ``initial`` to
        also contain the data from the :term:`Translations Model` if it can be
        found.

    .. method:: save(self, commit=True)
    
        Saves both the :term:`Shared Model` and :term:`Translations Model` and
        returns a combined model. The :term:`Translations Model` is either
        altered if it already exists on the :term:`Shared Model` for the current
        language (which is fetched from the ``language_code`` field on the form
        or the current active language) or newly created.
        
        .. note:: Other than in a normal :class:`django.forms.ModelForm`, this
                  method creates two queries instead of one. 

    .. method:: _post_clean(self)

        Ensures the correct translation is loaded into **self.instance**.
        It tries to load the language specified in the form's **language_code**
        field from the database, and calls
        :meth:`~hvad.models.TranslatableModel.translate` if it does not exist yet.

**********************
BaseTranslationFormSet
**********************

.. class:: BaseTranslationFormSet(BaseInlineFormSet)

    .. attribute:: instance

        An instance of a :class:`~hvad.models.TranslatableModel` that the formset
        works on the translations of. Its untranslatable fields will be used while
        validating and saving the translations.

    .. method:: order_translations(self, qs)

        Is given a queryset over the :term:`Translations Model`, that it should
        alter and return. This is used for adding **order_by** clause that will
        define the order in which languages will show up in the formset.

        Default implementation orders by **language_code**. If overriding this
        method, the default implementation should not be called.

    .. method:: clean(self)

        Performs translation-specific cleaning of the form. Namely, it combines
        each form's translation with :attr:`instance` then calls
        :meth:`~django.db.models.Model.full_clean` on the full object.

        It also ensures the last translation of an object cannot be deleted
        (unless adding a new translation at the same time).

    .. method:: _save_translation(self, form, commit=True)

        Saves one of the formset's forms to the database. It is used by both
        :meth:`save_new` and :meth:`save_existing`. It works by combining the
        form's translation with :attr:`instance`'s untranslatable fields, then
        saving the whole object, triggering any custom
        :meth:`~django.db.models.Model.save` method or related signal handlers.

    .. method:: save_new(self, form, commit=True)

        Saves a new translation. Called from
        :meth:`~django.forms.formsets.BaseInlineFormSet.save`.

    .. method:: save_existing(self, form, instance, commit=True)

        Saves an existing, updated translation. Called from
        :meth:`~django.forms.formsets.BaseInlineFormSet.save`.

    .. method:: add_fields(self, form, index)

        Adds a **language_code** field if it is not defined on the translation
        form.
