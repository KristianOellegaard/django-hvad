from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from django.utils.translation import get_language
from nani.descriptors import LanguageCodeAttribute, TranslatedAttribute
from nani.manager import TranslationManager, TranslationsModelManager
from nani.utils import SmartGetFieldByName
from types import MethodType


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
    if not hasattr(Meta, 'db_table'):
        Meta.db_table = model._meta.db_table + '%stranslation' % getattr(settings, 'NANI_TABLE_NAME_SEPARATOR', '_')
    name = '%sTranslation' % model.__name__
    attrs = {}
    attrs.update(fields)
    attrs['Meta'] = Meta
    attrs['__module__'] = model.__module__
    attrs['objects'] = TranslationsModelManager()
    attrs['language_code'] = models.CharField(max_length=15, db_index=True)
    # null=True is so we can prevent cascade deletion
    attrs['master'] = models.ForeignKey(model, related_name=related_name,
                                        editable=False, null=True)
    # Create and return the new model
    translations_model = ModelBase(name, (BaseTranslationModel,), attrs)
    bases = (model.DoesNotExist, translations_model.DoesNotExist,)
    DNE = type('DoesNotExist', bases, {})
    translations_model.DoesNotExist = DNE
    opts = translations_model._meta
    opts.shared_model = model
    return translations_model


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
    def __init__(self, *args, **kwargs):
        super(BaseTranslationModel, self).__init__(*args, **kwargs)
        
    class Meta:
        abstract = True
        

class TranslatableModelBase(ModelBase):
    """
    Metaclass for models with translated fields (TranslatableModel)
    """
    def __new__(cls, name, bases, attrs):
        super_new = super(TranslatableModelBase, cls).__new__
        parents = [b for b in bases if isinstance(b, TranslatableModelBase)]
        if not parents:
            # If this isn't a subclass of TranslatableModel, don't do anything special.
            return super_new(cls, name, bases, attrs)
        new_model = super_new(cls, name, bases, attrs)
        if not isinstance(new_model.objects, TranslationManager):
            raise ImproperlyConfigured(
                "The default manager on a TranslatableModel must be a "
                "TranslationManager instance or an instance of a subclass of "
                "TranslationManager, the default manager of %r is not." %
                new_model)
        
        opts = new_model._meta
        if opts.abstract:
            return new_model
        
        found = False
        for relation in new_model.__dict__.keys():
            try:
                obj = getattr(new_model, relation)
            except AttributeError:
                continue
            if not hasattr(obj, 'related'):
                continue
            if not hasattr(obj.related, 'model'):
                continue
            if issubclass(obj.related.model, BaseTranslationModel):
                if found:
                    raise ImproperlyConfigured(
                        "A TranslatableModel can only define one set of "
                        "TranslatedFields, %r defines more than one" %
                        new_model)
                else:
                    new_model.contribute_translations(obj.related)
                    found = True

        if not found:
            raise ImproperlyConfigured(
                "No TranslatedFields found on %r, subclasses of "
                "TranslatableModel must define TranslatedFields." % new_model
            )
        
        post_save.connect(new_model.save_translations, sender=new_model, weak=False)
        
        if not isinstance(opts.get_field_by_name, SmartGetFieldByName):
            smart_get_field_by_name = SmartGetFieldByName(opts.get_field_by_name)
            opts.get_field_by_name = MethodType(smart_get_field_by_name , opts,
                                                opts.__class__)
        
        return new_model
    

class NoTranslation(object):
    pass

class TranslatableModel(models.Model):
    """
    Base model for all models supporting translated fields (via TranslatedFields).
    """
    __metaclass__ = TranslatableModelBase
    
    # change the default manager to the translation manager
    objects = TranslationManager()
    
    class Meta:
        abstract = True
    
    def __init__(self, *args, **kwargs):
        tkwargs = {} # translated fields
        skwargs = {} # shared fields
        
        if 'master' in kwargs.keys():
            raise RuntimeError(
                    "Cannot init  %s class with a 'master' argument" % \
                    self.__class__.__name__
            )
        
        # filter out all the translated fields (including 'master' and 'language_code')
        primary_key_names = ('pk', self._meta.pk.name)
        for key in kwargs.keys():
            if key in self._translated_field_names:
                if not key in primary_key_names:
                    # we exclude the pk of the shared model
                    tkwargs[key] = kwargs.pop(key)
        if not tkwargs.keys():
            # if there where no translated options, then we assume this is a
            # regular init and don't want to do any funky stuff
            super(TranslatableModel, self).__init__(*args, **kwargs)
            return
        
        # there was at least one of the translated fields (or a language_code) 
        # in kwargs. We need to do magic.
        # extract all the shared fields (including the pk)
        for key in kwargs.keys():
            if key in self._shared_field_names:
                skwargs[key] = kwargs.pop(key)
        # do the regular init minus the translated fields
        super(TranslatableModel, self).__init__(*args, **skwargs)
        # prepopulate the translations model cache with an translation model
        tkwargs['language_code'] = tkwargs.get('language_code', get_language())
        tkwargs['master'] = self
        translated = self._meta.translations_model(*args, **tkwargs)
        setattr(self, self._meta.translations_cache, translated)
    
    @classmethod
    def contribute_translations(cls, rel):
        """
        Contribute translations options to the inner Meta class and set the
        descriptors.
        
        This get's called from TranslatableModelBase.__new__
        """
        opts = cls._meta
        opts.translations_accessor = rel.get_accessor_name()
        opts.translations_model = rel.model
        opts.translations_cache = '%s_cache' % rel.get_accessor_name()
        trans_opts = opts.translations_model._meta
        
        # Set descriptors
        ignore_fields = [
            'pk',
            'master',
            opts.translations_model._meta.pk.name,
        ]
        for field in trans_opts.fields:
            if field.name in ignore_fields:
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
            if not trans.master_id:
                trans.master = instance
            trans.save()
    
    def translate(self, language_code):
        """
        Returns an Model instance in the specified language.
        Does NOT check if the translation already exists!
        Does NOT interact with the database.
        
        This will refresh the translations cache attribute on the instance.
        """
        tkwargs = {
            'language_code': language_code,
            'master': self,
        }
        translated = self._meta.translations_model(**tkwargs)
        setattr(self, self._meta.translations_cache, translated)
        return self
    
    def safe_translation_getter(self, name, default=None):
        cache = getattr(self, self._meta.translations_cache, None)
        if not cache:
            return default
        return getattr(cache, name, default)

    def lazy_translation_getter(self, name, default=None):
        """
        Lazy translation getter that fetches translations from DB in case the instance is currently untranslated and
        saves the translation instance in the translation cache
        """
        cache = getattr(self, self._meta.translations_cache, NoTranslation)
        trans = self._meta.translations_model.objects.filter(master__pk=self.pk)
        if not cache and cache != NoTranslation and not trans.exists(): # check if there is no translations
            return default
        elif getattr(cache, name, NoTranslation) == NoTranslation and trans.exists(): # We have translations, but no specific translation cached
            trans_in_own_language = trans.filter(language_code=get_language())
            if trans_in_own_language.exists():
                trans = trans_in_own_language[0]
            else:
                trans = trans[0]
            setattr(self, self._meta.translations_cache, trans)
            return getattr(trans, name)
        return getattr(cache, name)
    
    def get_available_languages(self):
        manager = self._meta.translations_model.objects
        return manager.filter(master=self).values_list('language_code', flat=True)
    
    #===========================================================================
    # Internals
    #===========================================================================
    
    @property
    def _shared_field_names(self):
        if getattr(self, '_shared_field_names_cache', None) is None:
            self._shared_field_names_cache = self._meta.get_all_field_names()
        return self._shared_field_names_cache
    @property
    def _translated_field_names(self):
        if getattr(self, '_translated_field_names_cache', None) is None:
            self._translated_field_names_cache = self._meta.translations_model._meta.get_all_field_names()
        return self._translated_field_names_cache
