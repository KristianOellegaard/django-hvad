from django.core.exceptions import FieldError
from django.forms.forms import get_declared_fields
from django.forms.models import (ModelForm, ModelFormMetaclass, ModelFormOptions, 
    fields_for_model, model_to_dict, save_instance)
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
        if "Meta" in attrs:
            meta = attrs["Meta"]
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
        # End 1.3 fix
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
            if not sfieldnames:
                sfieldnames = None
            if not tfieldnames:
                tfieldnames = None  
            
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
        if instance is not None:
            trans = get_cached_translation(instance)
            if not trans:
                try:
                    trans = get_translation(instance)
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
            if not trans:
                try:
                    trans = get_translation(self.instance, language_code)
                except trans_model.DoesNotExist:
                    trans = trans_model()
        else:
            trans = trans_model()
        trans = save_instance(self, trans, self._meta.fields, fail_message,
                              commit, construct=True)
        trans.language_code = language_code
        trans.master = self.instance
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
        else:
            language_code = self.cleaned_data.get('language_code', get_language())
            self.instance = self.instance.translate(language_code)
            self.instance.save(False)
        return super(TranslatableModelForm, self)._post_clean()