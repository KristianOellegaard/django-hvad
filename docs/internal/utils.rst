#################
:mod:`nani.utils`
#################

.. module:: nani.utils

.. function:: combine(trans)

    Combines a :term:`Shared Model` with a :term:`Translations Model` by taking
    the :term:`Translations Model` and setting it onto the
    :term:`Shared Model`'s translations cache.

.. function:: get_cached_translation(instance)

    Returns the cached translation from an instance or ``None`.

.. function:: get_translation_aware_manager(model)

    Returns a manager for a normal model that is aware of translations and can
    filter over translated fields on translated models related to this normal
    model. 

.. class:: SmartGetFieldByName

    Smart version of the standard :meth:`get_field_by_name` on the options
    (meta) of Django models that raises a more useful exception when one tries
    to access translated fields with the wrong manager.

    .. method:: __init__(self, real)
    
    .. method:: __call__(self, meta, name)

.. function:: permissive_field_by_name(self, name)
    
    Returns the field from the :term:`Shared Model` or
    :term:`Translations Model`, if it is on either.