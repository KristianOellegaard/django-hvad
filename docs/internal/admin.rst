#################
:mod:`hvad.admin`
#################

.. module:: hvad.admin

.. function:: translatable_modelform_factory(model, form=TranslatableModelForm, fields=None, exclude=None, formfield_callback=None)
    
    The same as :func:`django.forms.models.modelform_factory` but uses ``type``
    instead of :class:`django.forms.models.ModelFormMetaclass` to create the
    form.
    

******************
TranslatableAdmin
******************

.. class:: TranslatableAdmin

    A subclass of :class:`django.contrib.admin.ModelAdmin` to be used for
    :class:`hvad.models.TranslatableModel` subclasses.
    
    .. attribute:: query_language_key
        
        The GET parameter to be used to switch the language, defaults to
        ``'language'``, which results in GET parameters like ``?language=en``.
    
    .. attribute:: form
    
        The form to be used for this admin class, defaults to
        :class:`hvad.forms.TranslatableModelForm` and if overwritten should
        always be a subclass of that class.
    
    .. attribute:: change_form_template
        
        We use ``'admin/hvad/change_form.html'`` here which extends the correct
        template using the logic from django admin, see
        :meth:`get_change_form_base_template`. This attribute should never
        change.
    
    .. method:: get_form(self, request, obj=None, **kwargs)
    
        Returns a form created by :func:`translatable_modelform_factory`.
    
    .. method:: all_translations(self, obj)
    
        A helper method to be used in :attr:`~django.contrib.admin.ModelAdmin.list_display`
        to show available languages.
    
    .. method:: render_change_form(self, request, context, add=False, change=False, form_url='', obj=None)
        
        Injects ``title``, ``language_tabs`` and ``base_template`` into the
        context before calling the :meth:`render_change_form` method on the
        super class.
        ``title`` just appends the current language to the end of the existing
        ``title`` in the context.
        ``language_tabs`` is the return value of :meth:`get_language_tabs`,
        ``base_template`` is the return value of
        :meth:`get_change_form_base_template`.
    
    .. method:: queryset(self, request)
        
        Calls :meth:`~hvad.manager.TranslationManager.untranslated`
        on the queryset returned by the call to the super class and returns that
        queryset. This allows showing all objects, even if they have no
        translation in current language, at the cost of more database queries.
    
    .. method:: _language(self, request)
    
        Returns the currently active language by trying to get the value from
        the GET parameters of the request using :attr:`query_language_key` or
        if that's not available, use
        :func:`~django.utils.translation.get_language`.

    .. method:: get_language_tabs(self, request, available_languages)
    
        Returns a list of triples. The triple contains the URL for the change
        view for that language, the verbose name of the language and whether
        it's the current language, available or empty. This is used in the
        template to show the language tabs.

    .. method:: get_change_form_base_template(self)
    
        Returns the appropriate base template to be used for this model.
        Tries the following templates:
        
        * admin/<applabel>/<modelname>/change_form.html
        * admin/<applabel>/change_form.html
        * admin/change_form.html
