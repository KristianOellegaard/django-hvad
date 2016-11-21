__all__ = ('FormData',)

#===============================================================================

class FormData(dict):
    ''' A dict that can be built from a form or formset instance, and will fill
    itself with request.POST-like data, allowing easier testing of form submissions.

    See forms_inline.TestTranslationsInline for example uses.
    '''
    def __init__(self, form_or_set):
        if hasattr(form_or_set, 'forms'):
            # It is a formset
            self.update(FormData(form_or_set.management_form))
            for form in form_or_set:
                self.update(FormData(form))
        else:
            # It is a form
            for field in form_or_set:
                value = field.value()
                initial = form_or_set.initial.get(field.name, field.field.initial)
                if value is not None:
                    self[field.html_name] = value
                if initial is not None:
                    self[field.html_initial_name] = initial

    def set_form_field(self, form, name, value):
        key = form[name].html_name
        if value is None:
            self.pop(key, None)
        else:
            self[key] = value

    def set_formset_field(self, formset, index, name, value):
        key = formset[index][name].html_name
        if value is None:
            self.pop(key, None)
        else:
            self[key] = value
