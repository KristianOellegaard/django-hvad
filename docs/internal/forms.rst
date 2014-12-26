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

        Uses Django's internal ``fields_for_model`` to get translated fields
        for model and fields declarations, then lets Django handle the other
        fields. Once it is done, it merges the translated fields, preserving order.

        Special handling is done to:

        * Prevent ``language_code`` from being used in any way by a field. This is
          because the form uses the ``language_code`` key in the ``cleaned_data``
          dictionary.
        * Prevent ``master`` from being recognized as a translated field. It is
          still a valid field name though.
        * Prevent the translations accessor from being used as a field.


**********************
TranslatableModelForm
**********************

.. class:: BaseTranslatableModelForm(BaseModelForm)

        The actual class supporting the features and methods, but lacking metaclass
        sugar. Inherited by :class:`~TranslatableModelForm` to attach the metaclass.
        Details are documented on that class.

.. class:: TranslatableModelForm(BaseTranslatableModelForm)

        Main form for editing :class:`~hvad.models.TranslatableModel` instances. As with
        regular django :class:`~django.forms.Form` classes, it can be used either
        directly or by passing it to :func:`~translatable_modelform_factory`.

        As an extension to regular forms, it handles translation and can be bound
        to a language. Binding to a language is done by setting :attr:`language`
        on the class (not the instance), either by inheriting it manually or
        using the factory function. Once bound to a language, the form is in
        **enforce** mode: all manipulations will be done using that language
        exclusively.

    .. attribute:: __metaclass__

        :class:`TranslatableModelFormMetaclass`

    .. attribute:: language

        The language the form is bound to. This is a class attribute. If present,
        the form is in **enforce** mode and will only deal with the specified
        language. See each method for the exact effects.

    .. method:: __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, initial=None, error_class=ErrorList, label_suffix=':', empty_permitted=False, instance=None)
    
        If this class is initialized with an instance, that has a translation
        loaded, it updates ``initial`` to also contain the data from the
        :term:`Translations Model`.

        If the form is not bound to a language, it will use the data from the
        instance. If the instance has no translation loaded, an attempt will be
        made at loading the current language, and if that fails the fields will
        be blank.

        If the form is in **enforce** mode and the instance does not have the
        correct translation loaded, then:

        * it will attempt to load it from the database.
        * if that fails, it will try to use the loaded translation on the instance.
        * if that fails (instance is untranslated), it will use default values.

        This process results in new translations being pre-populated with data
        from another language. Simply pass an instance in that language, or an
        untranslated instance if the behavior is not desired.

    .. method:: clean(self)

        If the form is in **enforce** mode, namely if it has a
        ``language`` property, apply the it to ``cleaned_data``. As usual, the
        special value ``None`` is replaced by current language.

        If the form is not bound to a language, this method does nothing. It is
        then possible to either use :meth:`save` in unbound mode or set the
        language code manually in ``cleaned_data['language_code']``.

        .. note:: A missing language is not the same as ``None``. While ``None``
                  will be replaced by current language and applied to ``cleaned_data``,
                  a missing language will not apply any language at all.

    .. method:: _post_clean(self)

        Loads a translation appropriate to the form mode. It is the very same that
        will be loaded by :meth:`save`. Doing it twice is needed because:

        * it must be done in ``_post_clean`` so that the correct translation is
          available for modifications. For instance, if the view updates some
          translated fields in between the call to ``is_valid()`` and ``save()``,
          or if a form defines a custom ``save()``.
        * it must also be done in ``save`` to ensure the language is correctly
          enforced when in **enforce** mode.

        This double check has no cost: unless the instance is changed by the view,
        the ``save()`` check will see the translation is correct and do nothing.

    .. method:: save(self, commit=True)

        Saves both the :term:`Shared Model` and :term:`Translations Model` and
        returns a combined model.

        The target language is determined as follows:

        * If a language is defined in ``cleaned_data``, that language is used.
        * Else, if the instance has a translation loaded, its language is used.
        * Else, the current language is used.

        Once the language is determined, the following happen:

        * If the object does not exist, it is created.
        * If the object exists but not in the target language, its shared fields
          are updated and a new translation is created.
        * If the object exists in the target language, it is updated.

        .. note:: The **enforce** mode has no direct impact on this method. Rather,
                  it affects the behavior of :meth:`clean`, which places relevant
                  language (or lack thereof) in ``cleaned_data``.


.. function:: translatable_modelform_factory(language, model, form=TranslatableModelForm, **kwargs)

    Attaches a language and a model class to the specified form and returns the
    resulting class. Additional arguments are any arguments accepted by Django's
    :func:`~django.forms.models.modelform_factory`, including ``fields`` and
    ``exclude``.

    Having a language attached, the returned form is in **enforce** mode.

.. function:: translatable_modelformset_factory(language, model, form=TranslatableModelForm, **kwargs)

    Creates a formset class, allowing edition a collection of instances of ``model``,
    all of them in the specified ``language``. Additional arguments are any
    argument accepted by Django's :func:`~django.forms.models.modelformset_factory`.

    Having a language attached, the returned formset is in **enforce** mode.

.. function:: translatable_inlineformset_factory(language, parent_model, model, form=TranslatableModelForm, **kwargs)

    Creates an inline formset, allowing edition of a collection of instances of
    ``model`` attached to an instance of ``parent_model``, all of those objects
    being in the specified ``language``. Additional arguments are any argument
    accepted by Django's :func:`~django.forms.models.inlineformset_factory`.

    Having a language attached, the returned formset is in **enforce** mode.


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
