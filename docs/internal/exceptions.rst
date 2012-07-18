######################
:mod:`hvad.exceptions`
######################

.. module:: hvad.exceptions

.. exception:: WrongManager

    Raised when trying to access the related manager of a foreign key pointing
    from a normal model to a translated model using the standard manager instead
    of one returned by :func:`hvad.utils.get_translation_aware_manager`. Used to
    give developers an easier to understand exception than a
    :exc:`django.core.exceptions.FieldError`. This exception is raised by the
    :class:`hvad.utils.SmartGetFieldByName` which gets patched onto the options
    (meta) of translated models.