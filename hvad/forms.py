import django
from django.conf import settings
from django.core.exceptions import FieldError, ValidationError
from django.forms.fields import CharField
from django.forms.formsets import formset_factory
from django.forms.models import (ModelForm, BaseModelForm, ModelFormMetaclass,
    fields_for_model, model_to_dict, construct_instance, BaseInlineFormSet, BaseModelFormSet,
    modelform_factory, inlineformset_factory)
if django.VERSION >= (1, 7):
    from django.forms.utils import ErrorList
else: #pragma: no cover
    from django.forms.util import ErrorList
from django.forms.widgets import Select
from django.utils.translation import get_language, ugettext as _
from hvad.compat import with_metaclass
from hvad.models import TranslatableModel, BaseTranslationModel
from hvad.utils import (set_cached_translation, get_cached_translation, load_translation)
try:
    from collections import OrderedDict
except ImportError: #pragma: no cover (python < 2.7)
    from django.utils.datastructures import SortedDict as OrderedDict
import warnings

veto_fields = ('id', 'master', 'master_id', 'language_code')

#=============================================================================

class TranslatableModelFormMetaclass(ModelFormMetaclass):
    ''' Metaclass used for forms with translatable fields.
        It wraps the regular ModelFormMetaclass to intercept translatable fields,
        otherwise it would choke. Translatable fields are then inserted back
        into the created class.
    '''
    def __new__(cls, name, bases, attrs):
        # Force presence of meta class, we need it
        meta = attrs.get('Meta')
        if meta is None:
            # if a base class has a Meta, inherit it
            base_meta = next(((base.Meta,) for base in bases if hasattr(base, 'Meta')), ())
            meta = attrs['Meta'] = type('Meta', base_meta + (object,), {})

        model = getattr(meta, 'model', None)
        fields = getattr(meta, 'fields', None)

        # Force exclusion of language_code as we use cleaned_data['language_code']
        exclude = meta.exclude = list(getattr(meta, 'exclude', ()))
        if fields is not None and 'language_code' in fields:
            raise FieldError('Field \'language_code\' is invalid.')

        # If a model is provided, handle translatable fields
        if model:
            if not issubclass(model, TranslatableModel):
                raise TypeError('TranslatableModelForm only works with TranslatableModel'
                                ' subclasses, which %s is not.' % model.__name__)

            # Additional exclusions
            exclude.append(model._meta.translations_accessor)
            if fields is not None and model._meta.translations_accessor in fields:
                raise FieldError('Field \'%s\' is invalid', model._meta.translations_accessor)

            # Get translatable fields
            tfields = fields_for_model(
                model._meta.translations_model,
                fields=fields,
                exclude=exclude + list(veto_fields),
                widgets=getattr(meta, 'widgets', None),
                formfield_callback=attrs.get('formfield_callback')
            )

            # Drop translatable fields from Meta.fields
            if fields is not None:
                meta.fields = [field for field in fields if tfields.get(field) is None]

        # Create the form class
        new_class = super(TranslatableModelFormMetaclass, cls).__new__(cls, name, bases, attrs)

        # Add translated fields into the form's base fields
        if model:
            if fields is None:
                # loop, as Django's variant of OrderedDict cannot consume generators
                for name, field in tfields.items():
                    if field is not None:
                        new_class.base_fields[name] = field
            else:
                # rebuild the fields to respect Meta.fields ordering
                new_class.base_fields = OrderedDict(
                    item for item in (
                        (name, new_class.base_fields.get(name, tfields.get(name)))
                        for name in fields
                    )
                    if item[1] is not None
                )
                # restore hijacked Meta.fields
                new_class._meta.fields = meta.fields = fields
        return new_class


#=============================================================================

class BaseTranslatableModelForm(BaseModelForm):
    ''' Base class for forms dealing with TranslatableModel
        It has two main responsibilities: loading translated fields into the form
        when __init__ialized and ensuring the right translation gets saved.
    '''
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):

        # Insert values of instance's translated fields into 'initial' dict
        object_data = {}
        enforce = hasattr(self, 'language')
        language = getattr(self, 'language', None) or get_language()

        if instance is not None:
            translation = load_translation(instance, language, enforce)
            if translation.pk:
                exclude = (tuple(self._meta.exclude or ()) + veto_fields)
                object_data.update(
                    model_to_dict(translation, self._meta.fields, exclude)
                )
        if initial is not None:
            object_data.update(initial)

        super(BaseTranslatableModelForm, self).__init__(
            data, files, auto_id, prefix, object_data,
            error_class, label_suffix, empty_permitted, instance
        )

    def clean(self):
        ''' If a language is set on the form, enforce it by overwriting it
            in the cleaned_data.
        '''
        data = super(BaseTranslatableModelForm, self).clean()
        if hasattr(self, 'language'):
            data['language_code'] = self.language
        return data

    def _post_clean(self):
        ''' Switch the translation on self.instance
            This cannot (and should not) be done in clean() because it could be
            overriden to change the language. Yet it should be done before save()
            to allow an overriden save to set some translated field values before
            invoking super().
        '''
        enforce = 'language_code' in self.cleaned_data
        language = self.cleaned_data.get('language_code') or get_language()
        translation = load_translation(self.instance, language, enforce)

        exclude = self._get_validation_exclusions()
        translation = construct_instance(self, translation, self._meta.fields, exclude)
        set_cached_translation(self.instance, translation)
        result = super(BaseTranslatableModelForm, self)._post_clean()
        return result

    def _get_validation_exclusions(self):
        exclude = super(BaseTranslatableModelForm, self)._get_validation_exclusions()
        for f in self.instance._meta.translations_model._meta.fields:
            if f.name in veto_fields:
                pass
            elif ((f.name not in self.fields) or
                (self._meta.fields and f.name not in self._meta.fields) or
                (self._meta.exclude and f.name in self._meta.exclude) or
                (f.name in self._errors)):
                exclude.append(f.name)
            else:
                form_field = self.fields[f.name]
                field_value = self.cleaned_data.get(f.name, None)
                if not f.blank and not form_field.required and field_value in form_field.empty_values:
                    exclude.append(f.name)
        return exclude

    def save(self, commit=True):
        ''' Saves the model
            If will always use the language specified in self.cleaned_data, with
            the usual None meaning 'call get_language()'. If instance has
            another language loaded, it gets reloaded with the new language.

            If no language is specified in self.cleaned_data, assume the instance
            is preloaded with correct language.
        '''
        assert self.is_valid(), ('Method save() must not be called on an invalid '
                                 'form. Check the result of .is_valid() before '
                                 'calling save().')

        # Get the right translation for object and language
        # It should have been done in _post_clean, but instance may have been
        # changed since.
        enforce = 'language_code' in self.cleaned_data
        language = self.cleaned_data.get('language_code') or get_language()
        translation = load_translation(self.instance, language, enforce)

        # Fill the translated fields with values from the form
        excludes = list(self._meta.exclude) + ['master', 'language_code']
        translation = construct_instance(self, translation,
                                         self._meta.fields, excludes)
        set_cached_translation(self.instance, translation)

        # Delegate shared fields to super()
        return super(BaseTranslatableModelForm, self).save(commit=commit)


if django.VERSION >= (1, 7):
    class TranslatableModelForm(with_metaclass(TranslatableModelFormMetaclass,
                                               BaseTranslatableModelForm)):
        pass
else: #pragma: no cover
    # Older django version have buggy metaclass
    class TranslatableModelForm(with_metaclass(TranslatableModelFormMetaclass,
                                               BaseTranslatableModelForm, ModelForm)):
        __metaclass__ = TranslatableModelFormMetaclass # Django 1.4 compatibility


#=============================================================================

def translatable_modelform_factory(language, model, form=TranslatableModelForm, *args, **kwargs):
    if not issubclass(form, TranslatableModelForm):
        raise TypeError('The form class given to translatable_modelform_factory '
                        'must be a subclass of hvad.forms.TranslatableModelForm')
    klass = modelform_factory(model, form, *args, **kwargs)
    klass.language = language
    return klass


def translatable_modelformset_factory(language, model, form=TranslatableModelForm,
                                      formfield_callback=None, formset=BaseModelFormSet,
                                      extra=1, can_delete=False, can_order=False,
                                      max_num=None, fields=None, exclude=None, **kwargs):

    # This Django API changes often, handle args we know and raise for others
    form_kwargs, formset_kwargs = {}, {}
    for key in ('widgets', 'localized_fields', 'labels', 'help_texts', 'error_messages'):
        if key in kwargs:
            form_kwargs[key] = kwargs.pop(key)
    for key in ('validate_max',):
        if key in kwargs:
            formset_kwargs[key] = kwargs.pop(key)
    if kwargs:
        raise TypeError('Unknown arguments %r for translatable_modelformset_factory. '
                        'If it is legit, it is probably new in Django. Please open '
                        'a ticket so we can add it.' % tuple(kwargs.keys()))

    form = translatable_modelform_factory(
        language, model, form=form, fields=fields, exclude=exclude,
        formfield_callback=formfield_callback, **form_kwargs
    )
    FormSet = formset_factory(form, formset, extra=extra, max_num=max_num,
                              can_order=can_order, can_delete=can_delete, **formset_kwargs)
    FormSet.model = model
    return FormSet


def translatable_inlineformset_factory(language, parent_model, model, form=TranslatableModelForm,
                                       formset=BaseInlineFormSet, fk_name=None,
                                       fields=None, exclude=None, extra=3,
                                       can_order=False, can_delete=True,
                                       max_num=None, formfield_callback=None, **kwargs):
    from django.forms.models import _get_foreign_key
    fk = _get_foreign_key(parent_model, model, fk_name=fk_name)
    if fk.unique:  #pragma: no cover (internal Django behavior)
        max_num = 1

    FormSet = translatable_modelformset_factory(language, model,
         form=form, formfield_callback=formfield_callback, formset=formset,
         extra=extra, can_delete=can_delete, can_order=can_order,
         fields=fields, exclude=exclude, max_num=max_num, **kwargs)
    FormSet.fk = fk
    return FormSet


#=============================================================================

class BaseTranslationFormSet(BaseInlineFormSet):
    """A kind of inline formset for working with an instance's translations.
    It keeps track of the real object and combine()s it to the translations
    for validation and saving purposes.
    It can delete translations, but will refuse to delete the last one.
    """
    def __init__(self, *args, **kwargs):
        super(BaseTranslationFormSet, self).__init__(*args, **kwargs)
        self.queryset = self.order_translations(self.queryset)

    def order_translations(self, qs):
        return qs.order_by('language_code')

    def clean(self):
        super(BaseTranslationFormSet, self).clean()

        # Trigger combined instance validation
        master = self.instance
        stashed = get_cached_translation(master)

        for form in self.forms:
            set_cached_translation(master, form.instance)
            exclusions = form._get_validation_exclusions()
            # fields from the shared model should not be validated
            exclusions.extend(f.name for f in master._meta.fields)
            try:
                master.clean()
            except ValidationError as e:
                form._update_errors(e)

        set_cached_translation(master, stashed)

        # Validate that at least one translation exists
        forms_to_delete = self.deleted_forms
        provided = [form for form in self.forms
                    if (getattr(form.instance, 'pk', None) is not None or
                        form.has_changed())
                       and not form in forms_to_delete]
        if len(provided) < 1:
            raise ValidationError(_('At least one translation must be provided'),
                                  code='notranslation')

    def _save_translation(self, form, commit=True):
        obj = form.save(commit=False)
        assert isinstance(obj, BaseTranslationModel)

        if commit:
            # We need to trigger custom save actions on the combined model
            stashed = set_cached_translation(self.instance, obj)
            self.instance.save()
            if hasattr(obj, 'save_m2m'): # pragma: no cover
                # cannot happen, but feature could be added, be ready
                obj.save_m2m()
            set_cached_translation(self.instance, stashed)
        return obj

    def save_new(self, form, commit=True):
        return self._save_translation(form, commit)

    def save_existing(self, form, instance, commit=True):
        return self._save_translation(form, commit)

    def add_fields(self, form, index):
        super(BaseTranslationFormSet, self).add_fields(form, index)
        # Add the language code automagically
        if not 'language_code' in form.fields:
            form.fields['language_code'] = CharField(
                required=True, initial=form.instance.language_code,
                widget=Select(choices=(('', '--'),)+settings.LANGUAGES)
            )
            # Add language_code to self._meta.fields so it is included in validation stage
            try:
                form._meta.fields.append('language_code')
            except AttributeError: #pragma: no cover
                form._meta.fields += ('language_code',)

        # Remove the master foreignkey, we have this from self.instance already
        if 'master' in form.fields:
            del form.fields['master']

def translationformset_factory(model, **kwargs):
    """ Works as a regular inlineformset_factory except for:
    - it is set up to work on the given model's translations table
    - it uses a BaseTranslationFormSet to handle combine() and language_code

    Basic use: MyModelTranslationsFormSet = translationformset_factory(MyModel)
    """
    defaults = {
        'formset': BaseTranslationFormSet,
        'fk_name': 'master',
    }
    defaults.update(kwargs)
    return inlineformset_factory(model, model._meta.translations_model, **defaults)

