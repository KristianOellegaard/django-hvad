##################
:mod:`nani.fields`
##################

.. module:: nani.fields

.. warning:: The classes in this module are probably going to be removed and are
             therefore left undocumented for now.


.. class:: ReverseTranslatedSingleRelatedObjectDescriptor

    .. method:: __set__(self, instance, value)
        
    .. method:: __get__(self, instance, instance_type=None)


.. class:: TranslatedForeignKey

    .. method:: __init__(self, to, *args, **kwargs)

    .. method:: contribute_to_class(self, cls, name)

    .. method:: contribute_to_related_class(self, cls, related)