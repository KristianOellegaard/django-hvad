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
