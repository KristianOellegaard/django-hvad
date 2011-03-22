.. _forms-public:

#####
Forms
#####

If you want to use your :class:`nani.models.TranslateableModel` in forms, you
have to subclass :class:`nani.forms.TranslateableModelForm` instead of
:class:`django.forms.ModelForm`.

Please note that you should not override
:meth:`nani.forms.TranslateableModelForm.save`, as it is a cruical part for the
form to work.