from django.core import checks
from django.db.models.fields import FieldDoesNotExist
from django.contrib.admin.checks import ModelAdminChecks
from .forms import TranslatableModelForm
from .models import TranslatableModel


class TranslatableAdminChecks(ModelAdminChecks):
    def check(self, cls, model, **kwargs):
        """ Include additional checks """
        errors = []
        errors.extend(self._check_model_translatable(cls, model))
        errors.extend(super(TranslatableAdminChecks, self).check(cls, model, **kwargs))
        return errors

    # Custom checks

    def _check_model_translatable(self, cls, model):
        """ Make sure the translatable admin is not fed a regular model """
        errors = []
        if not isinstance(model, TranslatableModel):
            errors.append(checks.Error("The model must be a subclass of TranslatableModel",
                                       hint=None, obj=cls, id='hvad.E001'))
        return []

    # From BaseModelAdminChecks

    def _check_raw_id_fields_item(self, cls, model, item, *args):
        """ Shift the stock check for valid translated fields so it happend on translations model """
        if _has_translated_field(model, item):
            model = model._meta.translations_model
        return super(TranslatableAdminChecks, self)._check_raw_id_fields_item(cls, model, item, *args)

    def _check_field_spec_item(self, cls, model, item, *args):
        if _has_translated_field(model, item):
            return []
        return super(TranslatableAdminChecks, self)._check_field_spec_item(cls, model, item, *args)

    def _check_form(self, cls, model):
        if hasattr(cls, 'form') and not issubclass(cls.form, TranslatableModelForm):
            return [checks.Error("The value of 'form' must inherit from 'TranslatableModelForm'.",
                                 hint=None, obj=cls, id='hvad.E002')]
        return super(TranslatableAdminChecks, self)._check_form(cls, model)

    def _check_prepopulated_fields_key(self, cls, model, field_name, *args):
        """ Shift the stock check for valid translated fields so it happend on translations model """
        if _has_translated_field(model, field_name):
            model = model._meta.translations_model
        return super(TranslatableAdminChecks, self)._check_prepopulated_fields_key(cls, model, field_name, *args)

    def _check_prepopulated_fields_value_item(self, cls, model, field_name, *args):
        """ Shift the stock check for valid translated fields so it happend on translations model """
        if _has_translated_field(model, field_name):
            model = model._meta.translations_model
        return super(TranslatableAdminChecks, self)._check_prepopulated_fields_value_item(cls, model, field_name, *args)

    def _check_ordering_item(self, cls, model, item, *args):
        field_name = item[1:] if item.startswith('-') else item
        if _has_translated_field(model, field_name):
            return [refer_to_translated_field(item, 'ordering', model, cls, id='hvad.E003')]
        return super(TranslatableAdminChecks, self)._check_ordering_item(cls, model, item, *args)

    def _check_readonly_fields_item(self, cls, model, item, *args):
        if _has_translated_field(model, item):
            return []
        return super(TranslatableAdminChecks, self)._check_readonly_fields_item(cls, model, item, *args)


    # From ModelAdminChecks

    def _check_list_display_item(self, cls, model, item, *args):
        """ Bypass the stock check for valid translated fields """
        if _has_translated_field(model, item):
            return []
        return super(TranslatableAdminChecks, self)._check_list_display_item(cls, model, item, *args)

    def _check_list_filter_item(self, cls, model, item, *args):
        if _has_translated_field(model, item):
            return [refer_to_translated_field(item, 'list_filter', model, cls, id='hvad.E004')]
        return super(TranslatableAdminChecks, self)._check_list_filter_item(cls, model, item, *args)

    def _check_list_editable_item(self, cls, model, item, *args):
        """ Replace stock check for translated fields for a more explicit message """
        if _has_translated_field(model, item):
            return [refer_to_translated_field(item, 'list_editable', model, cls, id='hvad.E005')]
        return super(TranslatableAdminChecks, self)._check_list_editable_item(cls, model, item, *args)



# ============================================================================

def _has_translated_field(model, name):
    try:
        model._meta.translations_model._meta.get_field(name)
    except FieldDoesNotExist:
        return False
    return True

def refer_to_translated_field(field, option, model, obj, id):
    return [
        checks.Error(
            "The value of '%s' refers to translated field '%s' of '%s.%s'." % (
                option, field, model._meta.app_label, model._meta.object_name
            ),
            hint="Translated fields are not supported in '%s' yet." % (option,),
            obj=obj,
            id=id,
        ),
    ]
