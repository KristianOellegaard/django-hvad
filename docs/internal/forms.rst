#################
:mod:`nani.forms`
#################


.. class:: TranslateableModelFormMetaclass

    .. method:: __new__(cls, name, bases, attrs)


.. class:: TranslateableModelForm(ModelForm)

    .. attribute:: __metaclass__

    .. method:: __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, initial=None, error_class=ErrorList, label_suffix=':', empty_permitted=False, instance=None)

    .. method:: save(self, commit=True)