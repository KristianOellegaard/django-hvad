#######################
:mod:`hvad.descriptors`
#######################

.. module:: hvad.descriptors


**************
BaseDescriptor
**************

.. class:: BaseDescriptor

    Base class for the descriptors, should not be used directly.
        
    .. attribute:: opts
    
        The options (meta) of the model.

    .. method:: translation(self, instance)
    
        Get the cached translation object on an instance. If no translation is
        cached yet, use the :func:`~django.utils.translation.get_language` function
        to get the current language, load it from the database and cache it on the
        instance.

        If no translation is cached, and no translation exists for current language,
        raise an :exc:`~exceptions.AttributeError`.


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
        the model instead of an instance) it returns the field object itself,
        allowing introspection of the model.

        Starting from Django 1.7, calling :func:`getattr` on a translated field
        before the App Registry is initialized raises an
        :exc:`~exceptions.AttributeError`.

    .. method:: __set__(self, instance, value)
    
        Sets the value on the attribute on the translation object using
        :meth:`BaseDescriptor.translation` if an instance is given, if no 
        instance is given, raises an :exc:`~exceptions.AttributeError`.

    .. method:: __delete__(self, instance)
    
        Deletes the attribute on the translation object using
        :meth:`BaseDescriptor.translation` if an instance is given, if no 
        instance is given, raises an :exc:`~exceptions.AttributeError`.


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