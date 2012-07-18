.. _forms-public:

#####
Forms
#####

If you want to use your :term:`Translated Model` in forms, you
have to subclass :class:`hvad.forms.TranslatableModelForm` instead of
:class:`django.forms.ModelForm`.

Please note that you should not override
:meth:`hvad.forms.TranslatableModelForm.save`, as it is a crucial part for the
form to work.
