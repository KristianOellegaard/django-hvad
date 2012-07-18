#######################
:mod:`hvad.descriptors`
#######################

.. module:: hvad.descriptors

.. class:: NULL

    A pseudo type used internally to distinguish between ``None`` and no value
    given. 


**************
BaseDescriptor
**************

.. class:: BaseDescriptor

    Base class for the descriptors, should not be used directly.
        
    .. attribute:: opts
    
        The options (meta) of the model.

    .. method:: translation(self, instance)
    
        Get the cached translation object on an instance, or get it from the
        database and cache it on the instance.


*******************
TranslatedAttribute
*******************

.. class:: TranslatedAttribute

    Standard descriptor for translated fields on the :term:`Shared Model`.

    .. attribute:: name
        
        The name of this attribute
        
    .. attribute:: opts
    
        The options (meta) of the model.

    .. method:: __get__(self, instance, instance_type=None)
    
        Gets the attribute from the translation object using
        :meth:`BaseDescriptor.translation`. If no instance is given (used from
        the model instead of an instance) it returns the default value from the
        field.

    .. method:: __set__(self, instance, value)
    
        Sets the value on the attribute on the translation object using
        :meth:`BaseDescriptor.translation` if an instance is given, if no 
        instance is given, raises an :exc:`AttributeError`.

    .. method:: __delete__(self, instance)
    
        Deletes the attribute on the translation object using
        :meth:`BaseDescriptor.translation` if an instance is given, if no 
        instance is given, raises an :exc:`AttributeError`.


*********************
LanguageCodeAttribute
*********************

.. class:: LanguageCodeAttribute

    The language code descriptor is different than the other fields, since it's
    readonly. The getter is inherited from :class:`TranslatedAttribute`.

    .. method:: __set__(self, instance, value)
    
        Raises an attribute error.

    .. method:: __delete__(self, instance)
    
        Raises an attribute error.