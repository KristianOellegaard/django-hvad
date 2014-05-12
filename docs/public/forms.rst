.. _forms-public:

#####
Forms
#####

If you want to use your :term:`Translated Model` in forms, you
have to subclass :class:`hvad.forms.TranslatableModelForm` instead of
:class:`django.forms.ModelForm`.

Please be careful while overriding the :meth:`~hvad.forms.TranslatableModelForm.save`
or :meth:`~hvad.forms.TranslatableModelForm._post_clean` methods, as they are crucial
parts for the form to work.
