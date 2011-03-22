#######################
:mod:`nani.descriptors`
#######################


.. class:: NULL

.. class:: BaseDescriptor

    .. method:: __init__(self, opts)

    .. method:: translation(self, instance)


.. class:: TranslatedAttribute

    .. method:: __init__(self, opts, name)

    .. method:: __get__(self, instance, instance_type=None)

    .. method:: __set__(self, instance, value)

    .. method:: __delete__(self, instance)


.. class:: LanguageCodeAttribute

    .. method:: __init__(self, opts)

    .. method:: __set__(self, instance, value)

    .. method:: __delete__(self, instance)