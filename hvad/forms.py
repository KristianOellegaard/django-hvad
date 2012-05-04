from django.core.exceptions import FieldError
from django.forms.forms import get_declared_fields
from django.forms.formsets import formset_factory
from django.forms.models import (ModelForm, ModelFormMetaclass, ModelFormOptions, 
    fields_for_model, model_to_dict, save_instance, BaseInlineFormSet, BaseModelFormSet)
from django.forms.util import ErrorList
from django.forms.widgets import media_property
from django.utils.translation import get_language
from nani.models import TranslatableModel
from nani.utils import get_cached_translation, get_translation, combine


class TranslatableModelFormMetaclass(ModelFormMetaclass):
    def __new__(cls, name, bases, attrs):
        
        """
        Django 1.3 fix, that removes all Meta.fields and Meta.exclude
        fieldnames that are in the translatable model. This ensures
        that the superclass' init method doesnt throw a validation
        error
        """
        fields = []
        exclude = []
        fieldsets = []
        if "Meta" in attrs:
            meta = attrs["Meta"]
            if getattr(meta, "fieldsets", False):
                fieldsets = meta.fieldsets
                meta.fieldsets = []
            if getattr(meta, "fields", False):
                fields = meta.fields
                meta.fields = []
            if getattr(meta, "exclude", False):
                exclude = meta.exclude
                meta.exclude = []
        # End 1.3 fix
        
        super_new = super(TranslatableModelFormMetaclass, cls).__new__
        
        formfield_callback = attrs.pop('formfield_callback', None)
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super_new(cls, name, bases, attrs)
        
        # Start 1.3 fix
        if fields:
            new_class.Meta.fields = fields
        if exclude:
            new_class.Meta.exclude = exclude
        if fieldsets:
            new_class.Meta.fieldsets = fieldsets
        # End 1.3 fix

        if not getattr(new_class, "Meta", None):
            class Meta:
                exclude = ['language_code']
            new_class.Meta = Meta
        elif not getattr(new_class.Meta, 'exclude', None):
            new_class.Meta.exclude = ['language_code']
        elif getattr(new_class.Meta, 'exclude', False):
            if 'language_code' not in new_class.Meta.exclude:
                new_class.Meta.exclude.append("language_code")

        if 'Media' not in attrs:
            new_class.media = media_property(new_class)
        opts = new_class._meta = ModelFormOptions(getattr(new_class, 'Meta', attrs.get('Meta', None)))
        if opts.model:
            # bail out if a wrong model uses this form class
            if not issubclass(opts.model, TranslatableModel):
                raise TypeError(
                    "Only TranslatableModel subclasses may use TranslatableModelForm"
                )
            mopts = opts.model._meta
            
            shared_fields = mopts.get_all_field_names()
            
            # split exclude and include fieldnames into shared and translated
            sfieldnames = [field for field in opts.fields or [] if field in shared_fields]
            tfieldnames = [field for field in opts.fields or [] if field not in shared_fields]
            sexclude = [field for field in opts.exclude or [] if field in shared_fields]
            texclude = [field for field in opts.exclude or [] if field not in shared_fields]
            
            # required by fields_for_model
            if not sfieldnames :
                sfieldnames = None if not fields else []
            if not tfieldnames:
                tfieldnames = None if not fields else []
            
            # If a model is defined, extract form fields from it.
            sfields = fields_for_model(opts.model, sfieldnames, sexclude,
                                       opts.widgets, formfield_callback)
            tfields = fields_for_model(mopts.translations_model, tfieldnames,
                                       texclude, opts.widgets, formfield_callback)
            
            fields = sfields
            fields.update(tfields)
            
            # make sure opts.fields doesn't specify an invalid field
            none_model_fields = [k for k, v in fields.iteritems() if not v]
            missing_fields = set(none_model_fields) - \
                             set(declared_fields.keys())
            if missing_fields:
                message = 'Unknown field(s) (%s) specified for %s'
                message = message % (', '.join(missing_fields),
                                     opts.model.__name__)
                raise FieldError(message)
            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
            
            if new_class._meta.exclude:
                new_class._meta.exclude = list(new_class._meta.exclude)
            else:
                new_class._meta.exclude = []
                
            for field in (mopts.translations_accessor, 'master'):
                if not field in new_class._meta.exclude:
                    new_class._meta.exclude.append(field)
        else:
            fields = declared_fields
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        # always exclude the FKs
        return new_class


class TranslatableModelForm(ModelForm):
    __metaclass__ = TranslatableModelFormMetaclass

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        opts = self._meta
        model_opts = opts.model._meta
        object_data = {}
        language = getattr(self, 'language', get_language())
        if instance is not None:
            trans = get_cached_translation(instance)
            if not trans:
                try:
                    trans = get_translation(instance, language)
                except model_opts.translations_model.DoesNotExist:
                    trans = None
            if trans:
                object_data = model_to_dict(trans, opts.fields, opts.exclude)
        if initial is not None:
            object_data.update(initial)
        initial = object_data
        super(TranslatableModelForm, self).__init__(data, files, auto_id,
                                                     prefix, object_data,
                                                     error_class, label_suffix,
                                                     empty_permitted, instance)

    def save(self, commit=True):
        if self.instance.pk is None:
            fail_message = 'created'
            new = True
        else:
            fail_message = 'changed'
            new = False
        super(TranslatableModelForm, self).save(True)
        trans_model = self.instance._meta.translations_model
        language_code = self.cleaned_data.get('language_code', get_language())
        if not new:
            trans = get_cached_translation(self.instance)
            if not trans or trans.language_code != language_code:
                try:
                    trans = get_translation(self.instance, language_code)
                except trans_model.DoesNotExist:
                    trans = trans_model()
        else:
            trans = trans_model()

        trans.language_code = language_code
        trans.master = self.instance
        trans = save_instance(self, trans, self._meta.fields, fail_message,
                              commit, construct=True)
        return combine(trans)
        
    def _post_clean(self):
        if self.instance.pk:
            try:
                trans = trans = get_translation(self.instance, self.instance.language_code)
                trans.master = self.instance
                self.instance = combine(trans)
            except self.instance._meta.translations_model.DoesNotExist:
                language_code = self.cleaned_data.get('language_code', get_language())
                self.instance = self.instance.translate(language_code)
        return super(TranslatableModelForm, self)._post_clean()



class CleanMixin(object):
    def clean(self):
        data = super(CleanMixin, self).clean()
        data['language_code'] = self.language
        return data


def LanguageAwareCleanMixin(language):
    return type('BoundCleanMixin', (CleanMixin,), {'language': language})


def translatable_modelform_factory(language, model, form=TranslatableModelForm,
                                   fields=None, exclude=None,
                                   formfield_callback=None):
    # Create the inner Meta class. FIXME: ideally, we should be able to
    # construct a ModelForm without creating and passing in a temporary
    # inner class.

    # Build up a list of attributes that the Meta object will have.
    attrs = {'model': model}
    if fields is not None:
        attrs['fields'] = fields
    if exclude is not None:
        attrs['exclude'] = exclude

    # If parent form class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type('Meta', parent, attrs)

    # Give this new form class a reasonable name.
    class_name = model.__name__ + 'Form'

    # Class attributes for the new form class.
    form_class_attrs = {
        'Meta': Meta,
        'formfield_callback': formfield_callback
    }
    clean_mixin = LanguageAwareCleanMixin(language)
    return type(class_name, (clean_mixin, form,), form_class_attrs)

def translatable_modelformset_factory(language, model, form=TranslatableModelForm, formfield_callback=None,
                         formset=BaseModelFormSet,
                         extra=1, can_delete=False, can_order=False,
                         max_num=None, fields=None, exclude=None):
    """
    Returns a FormSet class for the given Django model class.
    """
    form = translatable_modelform_factory(language, model, form=form, fields=fields, exclude=exclude,
                             formfield_callback=formfield_callback)
    FormSet = formset_factory(form, formset, extra=extra, max_num=max_num,
                              can_order=can_order, can_delete=can_delete)
    FormSet.model = model
    return FormSet

def translatable_inlineformset_factory(language, parent_model, model, form=TranslatableModelForm,
                          formset=BaseInlineFormSet, fk_name=None,
                          fields=None, exclude=None,
                          extra=3, can_order=False, can_delete=True, max_num=None,
                          formfield_callback=None):
    """
    Returns an ``InlineFormSet`` for the given kwargs.

    You must provide ``fk_name`` if ``model`` has more than one ``ForeignKey``
    to ``parent_model``.
    """
    from django.forms.models import _get_foreign_key
    fk = _get_foreign_key(parent_model, model, fk_name=fk_name)
    # enforce a max_num=1 when the foreign key to the parent model is unique.
    if fk.unique:
        max_num = 1
    kwargs = {
        'form': form,
        'formfield_callback': formfield_callback,
        'formset': formset,
        'extra': extra,
        'can_delete': can_delete,
        'can_order': can_order,
        'fields': fields,
        'exclude': exclude,
        'max_num': max_num,
    }
    FormSet = translatable_modelformset_factory(language, model, **kwargs)
    FormSet.fk = fk
    return FormSet
