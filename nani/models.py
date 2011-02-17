from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from nani.descriptors import LanguageCodeAttribute, TranslatedAttribute
from nani.manager import TranslationManager

def create_translations_model(model, related_name, meta, **fields):
    """
    Create the translations model for the shared model 'model'.
    'related_name' is the related name for the reverse FK from the translations
    model.
    'meta' is a (optional) dictionary of attributes for the translations model's
    inner Meta class.
    'fields' is a dictionary of fields to put on the translations model.
    
    Two fields are enforced on the translations model:
    
        language_code: A 15 char, db indexed field.
        master: A ForeignKey back to the shared model.
        
    Those two fields are unique together, this get's enforced in the inner Meta
    class of the translations table
    """
    if not meta:
        meta = {}
    unique = [('language_code', 'master')]
    meta['unique_together'] = list(meta.get('unique_together', [])) + unique
    # Create inner Meta class 
    Meta = type('Meta', (object,), meta)
    name = '%sTranslation' % model.__name__
    attrs = {}
    attrs.update(fields)
    attrs['Meta'] = Meta
    attrs['__module__'] = model.__module__
    attrs['language_code'] = models.CharField(max_length=15, db_index=True)
    # null=True is so we can prevent cascade deletion
    attrs['master'] = models.ForeignKey(model, related_name=related_name, editable=False, null=True)
    # Create and return the new model
    return ModelBase(name, (BaseTranslationModel,), attrs)


class TranslatedFields(object):
    """
    Wrapper class to define translated fields on a model.
    """
    def __init__(self, meta=None, **fields):
        self.fields = fields
        self.meta = meta

    def contribute_to_class(self, cls, name):
        """
        Called from django.db.models.base.ModelBase.__new__
        """
        create_translations_model(cls, name, self.meta, **self.fields)


class BaseTranslationModel(models.Model):
    """
    Needed for detection of translation models. Due to the way dynamic classes
    are created, we cannot put the 'language_code' field on here.
    """
    class Meta:
        abstract = True
        

class TranslateableModelBase(ModelBase):
    """
    Metaclass for models with translated fields (TranslatableModel)
    """
    def __new__(cls, name, bases, attrs):
        super_new = super(TranslateableModelBase, cls).__new__
        parents = [b for b in bases if isinstance(b, TranslateableModelBase)]
        if not parents:
            # If this isn't a subclass of TranslateableModel, don't do anything special.
            return super_new(cls, name, bases, attrs)
        new_model = super_new(cls, name, bases, attrs)
        if not isinstance(new_model.objects, TranslationManager):
            raise ImproperlyConfigured("wrong manager")
        
        found = False
        local_field_names = [ff.name for ff in new_model._meta.fields]
        field_names = new_model._meta.get_all_field_names()
        for relation in [f for f in field_names if not f in local_field_names]:
            obj = getattr(new_model, relation)
            if not hasattr(obj, 'related'):
                continue
            if not hasattr(obj.related, 'model'):
                continue
            if issubclass(obj.related.model, BaseTranslationModel):
                if found:
                    raise ImproperlyConfigured("more than one")
                else:
                    new_model.contribute_translations(obj.related)
                    found = True

        if not found:
            raise ImproperlyConfigured("not found)")
        
        post_save.connect(new_model.save_translations, sender=new_model, weak=False)
        
        return new_model


class TranslateableModel(models.Model):
    """
    Base model for all models supporting translated fields (via TranslatedFields).
    """
    __metaclass__ = TranslateableModelBase
    
    # change the default manager to the translation manager
    objects = TranslationManager()
    
    class Meta:
        abstract = True
    
    @classmethod
    def contribute_translations(cls, rel):
        """
        Contribute translations options to the inner Meta class and set the
        descriptors.
        
        This get's called from TranslateableModelBase.__new__
        """
        opts = cls._meta
        opts.translations_accessor = rel.get_accessor_name()
        opts.translations_model = rel.model
        opts.translations_cache = '%s_cache' % rel.get_accessor_name()
        trans_opts = opts.translations_model._meta
        
        # Set descriptors
        for field in trans_opts.fields:
            if field.name == 'pk':
                continue
            if field.name == 'master':
                continue
            if field.name == opts.translations_model._meta.pk.name:
                continue
            if field.name == 'language_code':
                attr = LanguageCodeAttribute(opts)
            else:
                attr = TranslatedAttribute(opts, field.name)
            setattr(cls, field.name, attr)
    
    @classmethod
    def save_translations(cls, instance, **kwargs):
        """
        When this instance is saved, also save the (cached) translation
        """
        opts = cls._meta
        if hasattr(instance, opts.translations_cache):
            trans = getattr(instance, opts.translations_cache)
            trans.save()