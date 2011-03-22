#################
:mod:`nani.admin`
#################

.. function:: translateable_modelform_factory(model, form=TranslateableModelForm, fields=None, exclude=None, formfield_callback=None)


.. class:: TranslateableAdmin
    
    .. attribute:: query_language_key
    
    .. attribute:: form
    
    .. attribute:: change_form_template
    
    
    .. method:: get_form(self, request, obj=None, **kwargs)
    
    .. method:: all_translations(self, obj)
    
    .. method:: render_change_form(self, request, context, add=False, change=False, form_url='', obj=None)
    
    .. method:: queryset(self, request)
    
    .. method:: _language(self, request)

    .. method:: get_language_tabs(self, request, obj)

    .. method:: get_change_form_base_template(self)