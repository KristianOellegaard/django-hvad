.. _forms-public:

#####
Forms
#####

If you want to use your :term:`Translated Model` in forms, you
have to subclass :class:`nani.forms.TranslatableModelForm` instead of
:class:`django.forms.ModelForm`.

Please note that you should not override
:meth:`nani.forms.TranslatableModelForm.save`, as it is a cruical part for the
form to work.
