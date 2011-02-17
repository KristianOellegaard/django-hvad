from django.db import models
from django.db.models.query import QuerySet, ValuesQuerySet
from django.db.models.query_utils import Q
from django.utils.translation import get_language
from nani.utils import R, combine

class FieldTranslator(dict):
    """
    Translates *shared* field names from '<shared_field>' to
    'master__<shared_field>' and caches those names.
    """
    def __init__(self, manager):
        self.manager = manager
        self.shared_fields = tuple(self.manager.shared_model._meta.get_all_field_names()) + ('pk',)
        self.translated_fields  = tuple(self.manager.model._meta.get_all_field_names())
        super(FieldTranslator, self).__init__()
        
    def get(self, key):
        if not key in self:
            self[key] = self.build(key)
        return self[key]
    
    def build(self, key):
        if key.startswith(self.shared_fields):
            return 'master__%s' % key
        else:
            return key


class ValuesMixin(object):
    def _strip_master(self, key):
        if key.startswith('master__'):
            return key[8:]
        return key
       
    def iterator(self):
        for row in super(ValuesMixin, self).iterator():
            if isinstance(row, dict):
                yield dict([(self._strip_master(k), v) for k,v in row.items()])
            else:
                yield row

        
class TranslationMixin(QuerySet):
    """
    This is where things happen.
    
    To fully understand this project, you have to understand this class.
    
    Go through each method individually, maybe start with 'get', 'create' and
    'iterator'.
    
    IMPORTANT: the `model` attribute on this class is the *translated* Model,
    despite this being used as the queryset for the *shared* Model!
    """
    override_classes = {
        ValuesQuerySet: ValuesMixin,
    }
    
    def __init__(self, model=None, query=None, using=None, real=None):
        self._local_field_names = None
        self._field_translator = None
        self._real_manager = real
        self._language_code = None
        super(TranslationMixin, self).__init__(model=model, query=query, using=using)

    #===========================================================================
    # Helpers and properties (ITNERNAL!)
    #===========================================================================

    @property
    def translations_manager(self):
        """
        Get the (real) manager of translations model
        """
        return self.model.objects
    
    @property
    def shared_model(self):
        """
        Get the shared model class
        """
        return self._real_manager.model
        
    @property
    def field_translator(self):
        """
        Field translator for this manager
        """
        if self._field_translator is None:
            self._field_translator = FieldTranslator(self)
        return self._field_translator
        
    @property
    def shared_local_field_names(self):
        if self._local_field_names is None:
            self._local_field_names = self.shared_model._meta.get_all_field_names()
        return self._local_field_names
    
    def _translate_args_kwargs(self, *args, **kwargs):
        # Translated kwargs from '<shared_field>' to 'master__<shared_field>'
        # where necessary.
        newkwargs = {}
        for key, value in kwargs.items():
            newkwargs[self.field_translator.get(key)] = value
        # Translate args (Q objects) from '<shared_field>' to
        # 'master_<shared_field>' where necessary.
        newargs = []
        for q in args:
            newargs.append(self._recurse_q(q))
        return newargs, newkwargs
    
    def _translate_fieldnames(self, fieldnames):
        newnames = []
        for name in fieldnames:
            newnames.append(self.field_translator.get(name))
        return newnames        

    def _recurse_q(self, q):
        """
        Recursively translate fieldnames in a Q object.
        
        TODO: What happens if we span multiple relations?
        """
        newchildren =  []
        for child in q.children:
            if isinstance(child, R):
                newchildren.append(child)
            elif isinstance(child, Q):
                newq = self._recurse_q(child)
                newchildren.append(self._recurse_q(newq))
            else:
                key, value = child
                newchildren.append((self.field_translator.get(key), value))
        q.children = newchildren
        return q
    
    def _find_language_code(self, q):
        """
        Checks if it finds a language code in a Q object (and it's children).
        """
        language_code = None
        for child in q.children:
            if isinstance(child, Q):
                language_code = self._find_language_code(child)
            elif isinstance(child, tuple):
                key, value = child
                if key == 'language_code':
                    language_code = value
            if language_code:
                break
        return language_code
    
    def _split_kwargs(self, **kwargs):
        """
        Split kwargs into shared and translated fields
        """
        shared = {}
        translated = {}
        for key, value in kwargs.items():
            if key in self.shared_local_field_names:
                shared[key] = value
            else:
                translated[key] = value
        return shared, translated
    
    def _get_class(self, klass):
        for key, value in self.override_classes.items():
            if issubclass(klass, key):
                return type(value.__name__, (value, klass, TranslationMixin,), {})
        return klass
    
    def _get_shared_query_set(self):
        qs = super(TranslationMixin, self)._clone()
        qs.__class__ = QuerySet
        # un-select-related the 'master' relation
        del qs.query.select_related['master']
        accessor = self.shared_model._meta.translations_accessor
        # update using the real manager
        return self._real_manager.filter(**{'%s__in' % accessor:qs})
    
    #===========================================================================
    # Queryset/Manager API 
    #===========================================================================
    
    def language(self, language_code=None):
        if not language_code:
            language_code = get_language()
        self._language_code = language_code
        return self.filter(language_code=language_code)
        
    def create(self, **kwargs):
        """
        When we create an instance, what we actually need to do is create two
        separate instances: One shared, and one translated.
        For this, we split the 'kwargs' into translated and shared kwargs
        and set the 'master' FK from in the translated kwargs to the shared
        instance.
        If 'language_code' is not given in kwargs, set it to the current
        language.
        """
        tkwargs = {}
        for key in kwargs.keys():
            if not key in self.shared_local_field_names:
                tkwargs[key] = kwargs.pop(key)
        # enforce a language_code
        if 'language_code' not in tkwargs:
            if self._language_code:
                tkwargs['language_code'] = self._language_code
            else:
                tkwargs['language_code'] = get_language()
        # Allow a pre-existing master to be passed, but only if no shared fields
        # are given.
        if 'master' in tkwargs:
            if kwargs:
                raise RuntimeError(
                    "Cannot explicitly use a master (shared) instance and shared fields in create"
                )
        else:
            # create shared instance
            shared = self._real_manager.create(**kwargs)
            tkwargs['master'] = shared
        # create translated instance
        trans = self.translations_manager.create(**tkwargs)
        # return combined instance
        return combine(trans)
    
    def get(self, *args, **kwargs):
        """
        Get an object by querying the translations model and returning a 
        combined instance.
        """
        # Enforce a language_code to be used
        newargs, newkwargs = self._translate_args_kwargs(*args, **kwargs)
        # Enforce 'select related' onto 'master'
        # Get the translated instance
        found = False
        qs = self
        if 'language_code' in newkwargs:
            language_code = newkwargs.pop('language_code')
            qs = self.language(language_code)
        elif args:
            language_code = None
            for arg in args:
                if not isinstance(arg, Q):
                    continue
                language_code = self._find_language_code(arg)
                if language_code:
                    break
            if language_code:
                qs = self.language(language_code)
            else:
                qs = self.language()
        else:
            for where in qs.query.where.children:
                if where.children:
                    for child in where.children:
                        if child[0].field.name == 'language_code':
                            found = True
                            break
                if found:
                    break
            if not found:
                qs = self.language()
        # self.iterator already combines! Isn't that nice?
        return QuerySet.get(qs, *newargs, **newkwargs)

    def filter(self, *args, **kwargs):
        newargs, newkwargs = self._translate_args_kwargs(*args, **kwargs)
        return super(TranslationMixin, self).filter(*newargs, **newkwargs)

    def aggregate(self, *args, **kwargs):
        raise NotImplementedError()

    def latest(self, field_name=None):
        if field_name:
            field_name = self.field_translator.get(field_name)
        return super(TranslationMixin, self).latest(field_name)

    def in_bulk(self, id_list):
        raise NotImplementedError()

    def delete(self):
        self._get_shared_query_set().delete()
    delete.alters_data = True
    
    def delete_translations(self):
        self.update(master=None)
        super(TranslationMixin, self).delete()
    delete_translations.alters_data = True
        

    def update(self, **kwargs):
        shared, translated = self._split_kwargs(**kwargs)
        count = 0
        if translated:
            count += super(TranslationMixin, self).update(**translated)
        if shared:
            shared_qs = self._get_shared_query_set()
            count += shared_qs.update(**shared)
        return count
    update.alters_data = True

    def values(self, *fields):
        fields = self._translate_fieldnames(fields)
        return super(TranslationMixin, self).values(*fields)

    def values_list(self, *fields, **kwargs):
        fields = self._translate_fieldnames(fields)
        return super(TranslationMixin, self).values_list(*fields, **kwargs)

    def dates(self, field_name, kind, order='ASC'):
        raise NotImplementedError()

    def exclude(self, *args, **kwargs):
        raise NotImplementedError()

    def complex_filter(self, filter_obj):
        raise NotImplementedError()

    def annotate(self, *args, **kwargs):
        raise NotImplementedError()

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        fieldnames = self._translate_fieldnames(field_names)
        return super(TranslationMixin, self).order_by(*fieldnames)
    
    def reverse(self):
        raise NotImplementedError()

    def defer(self, *fields):
        raise NotImplementedError()

    def only(self, *fields):
        raise NotImplementedError()
    
    def _clone(self, klass=None, setup=False, **kwargs):
        kwargs.update({
            '_local_field_names': self._local_field_names,
            '_field_translator': self._field_translator,
            '_language_code': self._language_code,
            '_real_manager': self._real_manager,
        })
        if klass:
            klass = self._get_class(klass)
        else:
            klass = self.__class__
        return super(TranslationMixin, self)._clone(klass, setup, **kwargs)
    
    def __getitem__(self, item):
        return super(TranslationMixin, self).__getitem__(item)
    
    def iterator(self):
        for obj in super(TranslationMixin, self).iterator():
            # non-cascade-deletion hack:
            if not obj.master:
                yield obj
            else:
                yield combine(obj)


class TranslationManager(models.Manager):
    """
    Manager class for models with translated fields
    """
    #===========================================================================
    # API 
    #===========================================================================
    def language(self, language_code=None):
        return self.get_query_set().language(language_code)
    
    #===========================================================================
    # Internals
    #===========================================================================
    
    @property
    def translations_model(self):
        """
        Get the translations model class
        """
        return self.model._meta.translations_model

    def get_query_set(self):
        """
        Make sure that querysets inherit the methods on this manager (chaining)
        """
        if not hasattr(self, '_real_manager'):
            self.contribute_real_manager()
        qs = TranslationMixin(self.translations_model, using=self.db, real=self._real_manager)
        return qs.select_related('master')
    
    def contribute_to_class(self, model, name):
        super(TranslationManager, self).contribute_to_class(model, name)
        self.name = name
        self.contribute_real_manager()
        
    def contribute_real_manager(self):
        self._real_manager = models.Manager()
        self._real_manager.contribute_to_class(self.model, '_%s' % getattr(self, 'name', 'objects'))