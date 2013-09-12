from collections import defaultdict
import django
from django.conf import settings
from django.db import models, transaction, IntegrityError
from django.db.models.query import QuerySet, ValuesQuerySet, DateQuerySet
try:
    from django.db.models.query import CHUNK_SIZE
except ImportError:
    CHUNK_SIZE = 100
from django.db.models.query_utils import Q
from django.utils.translation import get_language
from hvad.fieldtranslator import translate
from hvad.utils import combine
import django
import logging
import sys

logger = logging.getLogger(__name__)
DJANGO_VERSION = django.get_version()

# maybe there should be an extra settings for this
FALLBACK_LANGUAGES = [ code for code, name in settings.LANGUAGES ]

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
        """
        Checks if the selected field is a shared field
        and in that case, prefixes it with master___
        It also handles - and ? in case its called by
        order_by()
        """
        if key == "?":
            return key
        if key.startswith("-"):
            prefix = "-"
            key = key[1:]
        else:
            prefix = ""
        if key.startswith(self.shared_fields):
            return '%smaster__%s' % (prefix, key)
        else:
            return '%s%s' % (prefix, key)


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


class DatesMixin(object):
    pass


#===============================================================================
# Default 
#===============================================================================

        
class TranslationQueryset(QuerySet):
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
        DateQuerySet: DatesMixin,
    }
    
    def __init__(self, model=None, query=None, using=None, real=None):
        self._local_field_names = None
        self._field_translator = None
        self._real_manager = real
        self._fallback_manager = None
        self._language_code = None
        self._forced_unique_fields = []  # Used for select_related
        super(TranslationQueryset, self).__init__(model=model, query=query, using=using)

        # After super(), make sure we retrieve the shared model:
        if not self.query.select_related:
            self.query.add_select_related(('master',))


    #===========================================================================
    # Helpers and properties (INTERNAL!)
    #===========================================================================

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
        # 'master__<shared_field>' where necessary.
        newargs = []
        for q in args:
            newargs.append(self._recurse_q(q))
        return newargs, newkwargs
    
    def _translate_fieldnames(self, fieldnames):
        newnames = []
        for name in fieldnames:
            newnames.append(self.field_translator.get(name))
        return newnames

    def _reverse_translate_fieldnames_dict(self, fieldname_dict):
        """
        Helper function to make sure the user doesnt get "bothered"
        with the construction of shared/translated model

        Translates e.g.
        {'master__number_avg': 10} to {'number__avg': 10}

        """
        newdict = {}
        for key, value in fieldname_dict.items():
            if key.startswith("master__"):
                key = key.replace("master__", "")
            newdict[key] = value
        return newdict

    def _recurse_q(self, q):
        """
        Recursively translate fieldnames in a Q object.
        
        TODO: What happens if we span multiple relations?
        """
        newchildren =  []
        for child in q.children:
            if isinstance(child, Q):
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
                return type(value.__name__, (value, klass, TranslationQueryset,), {})
        return klass
    
    def _get_shared_query_set(self):
        qs = super(TranslationQueryset, self)._clone()
        qs.__class__ = QuerySet
        # un-select-related the 'master' relation
        del qs.query.select_related['master']
        accessor = self.shared_model._meta.translations_accessor
        # update using the real manager
        return self._real_manager.filter(**{'%s__in' % accessor:qs})

    def _scan_for_language_where_node(self, children):
        found = False
        for node in children:
            try:
                field_name = node[0].field.name
            except TypeError:
                if node.children:
                    found = self._scan_for_language_where_node(node.children)
            else:
                found = field_name == 'language_code'

            if found:
                # No need to continue
                return True
    
    #===========================================================================
    # Queryset/Manager API 
    #===========================================================================
    
    def language(self, language_code=None):
        if not language_code:
            language_code = get_language()
        self._language_code = language_code
        return self.filter(language_code=language_code)
    
    def __getitem__(self, k):
        """
        Handle getitem special since self.iterator is called *after* the
        slicing happens, when it's no longer possible to filter a queryest.
        Therefore the check for _language_code must be done here.
        """
        if not self._language_code:
            return self.language().__getitem__(k)
        return super(TranslationQueryset, self).__getitem__(k)
        
    def create(self, **kwargs):
        if 'language_code' not in kwargs:
            if self._language_code:
                kwargs['language_code'] = self._language_code
            else:
                kwargs['language_code'] = get_language()
        obj = self.shared_model(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db)
        return obj
    
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
            found = True
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
                found = True
        else:
            found = self._scan_for_language_where_node(qs.query.where.children)
        if not found:
            qs = self.language()
        # self.iterator already combines! Isn't that nice?
        return QuerySet.get(qs, *newargs, **newkwargs)

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert kwargs, \
                'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        lookup = kwargs.copy()
        for f in self.model._meta.fields:
            if f.attname in lookup:
                lookup[f.name] = lookup.pop(f.attname)
        try:
            self._for_write = True
            return self.get(**lookup), False
        except self.model.DoesNotExist:
            try:
                params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
                params.update(defaults)
                # START PATCH
                if 'language_code' not in params:
                    if self._language_code:
                        params['language_code'] = self._language_code
                    else:
                        params['language_code'] = get_language()
                obj = self.shared_model(**params)
                # END PATCH
                sid = transaction.savepoint(using=self.db)
                obj.save(force_insert=True, using=self.db)
                transaction.savepoint_commit(sid, using=self.db)
                return obj, True
            except IntegrityError:
                transaction.savepoint_rollback(sid, using=self.db)
                exc_info = sys.exc_info()
                try:
                    return self.get(**lookup), False
                except self.model.DoesNotExist:
                    # Re-raise the IntegrityError with its original traceback.
                    raise exc_info[1]

    def filter(self, *args, **kwargs):
        newargs, newkwargs = self._translate_args_kwargs(*args, **kwargs)
        return super(TranslationQueryset, self).filter(*newargs, **newkwargs)

    def aggregate(self, *args, **kwargs):
        """
        Loops over all the passed aggregates and translates the fieldnames
        """
        newargs, newkwargs = [], {}
        for arg in args:
            arg.lookup = self._translate_fieldnames([arg.lookup])[0]
            newargs.append(arg)
        for key in kwargs:
            value = kwargs[key]
            value.lookup = self._translate_fieldnames([value.lookup])[0]
            newkwargs[key] = value
        response = super(TranslationQueryset, self).aggregate(*newargs, **newkwargs)
        return self._reverse_translate_fieldnames_dict(response)

    def latest(self, field_name=None):
        if field_name:
            field_name = self.field_translator.get(field_name)
        return super(TranslationQueryset, self).latest(field_name)

    def in_bulk(self, id_list):
        raise NotImplementedError()

    def delete(self):
        qs = self._get_shared_query_set()
        qs.delete()
    delete.alters_data = True
    
    def delete_translations(self):
        self.update(master=None)
        super(TranslationQueryset, self).delete()
    delete_translations.alters_data = True
        
    def update(self, **kwargs):
        shared, translated = self._split_kwargs(**kwargs)
        count = 0
        if translated:
            count += super(TranslationQueryset, self).update(**translated)
        if shared:
            shared_qs = self._get_shared_query_set()
            count += shared_qs.update(**shared)
        return count
    update.alters_data = True

    def values(self, *fields):
        fields = self._translate_fieldnames(fields)
        return super(TranslationQueryset, self).values(*fields)

    def values_list(self, *fields, **kwargs):
        fields = self._translate_fieldnames(fields)
        return super(TranslationQueryset, self).values_list(*fields, **kwargs)

    def dates(self, field_name, kind=None, order='ASC'):
        field_name = self.field_translator.get(field_name)
        if int(django.get_version().split('.')[1][0]) <= 2:
            from nani.compat.date import DateQuerySet
            return self._clone(klass=DateQuerySet, setup=True,
                _field_name=field_name, _kind=kind, _order=order)
        return super(TranslationQueryset, self).dates(field_name, kind=kind, order=order)

    def exclude(self, *args, **kwargs):
        newargs, newkwargs = self._translate_args_kwargs(*args, **kwargs)
        return super(TranslationQueryset, self).exclude(*newargs, **newkwargs)

    def select_related(self, *fields):
        """
        Include other models in this query.
        This is complex but allows retreiving related models and their
        translations with a single query.
        """
        if not fields:
            raise NotImplementedError("To use select_related on a translated model, you must provide a list of fields.")
        related_model_keys = ['master']
        related_model_explicit_joins = []
        related_model_extra_filters = []
        forced_unique_fields = []
        for query_key in fields:
            bits = query_key.split('__')
            try:
                field, model, direct, _ = self.shared_model._meta.get_field_by_name.real(bits[0])
                query_key = 'master__%s' % query_key
            except models.FieldDoesNotExist:
                field, model, direct, _ = self.model._meta.get_field_by_name(bits[0])
            if not model:
                model = field.rel.to if direct else field.model

            if hasattr(model._meta, 'translations_accessor'):  # if issubclass(model, TranslatableModel):
                # This is a relation to a translated model,
                # so we need to select_related both the model and its translation model
                if len(bits) > 1:
                    raise NotImplementedError("Deep select_related with translated models not yet supported")
                related_model_keys.append(query_key)  # Select the related model
                related_model_keys.append('%s__%s' % (query_key, model._meta.translations_accessor))  # and its translation model

                # We need to force this to be a LEFT OUTER join, so we explicitly add the join.
                # Django 1.6 changes the footprint of the Query.join method. See https://code.djangoproject.com/ticket/19385
                if DJANGO_VERSION < '1.6':
                    join_data = (field.model._meta.db_table, model._meta.db_table, bits[0] + "_id", 'id')
                else:
                    join_data = (field, (field.model._meta.db_table, model._meta.db_table, ((bits[0] + "_id", 'id'),)))
                related_model_explicit_joins.append(join_data)
                # And we are going to force the query to treat the language join as one-to-one,
                # so we need to filter for the desired language:
                related_model_extra_filters.append(('%s__%s__language_code' % (query_key, model._meta.translations_accessor), self._language_code))
                rel_field_to_force = getattr(model, model._meta.translations_accessor).related.field
                if not rel_field_to_force._unique:
                    # The filter that we set up above essentially makes the related translations table
                    # a one-to-one join with the related shared table, so we need to use a hack that
                    # forces the query compiler to treat the join as one-to-one:
                    # The following will defer "model.translations.related.field._unique = True"
                    forced_unique_fields.append(rel_field_to_force)
            else:
                related_model_keys.append(query_key)
        obj = self._clone()
        obj.query.get_compiler(obj.db).fill_related_selections()  # seems to be necessary; not sure why
        for j in related_model_explicit_joins:
            if DJANGO_VERSION >= '1.6':
                kwargs = {'join_field': j[0]}
                j = j[1]
            else:
                kwargs = {}
            obj.query.join(j, outer_if_first=True, **kwargs)
        for f in related_model_extra_filters:
            f1 = {f[0]: f[1]}
            f2 = {f[0]: None}  # Allow select_related() to fetch objects with a relation set to NULL
            obj.query.add_q( Q(**f1) | Q(**f2) )
        obj._forced_unique_fields.extend(forced_unique_fields)
        obj.query.add_select_related(related_model_keys)

        return obj

    def complex_filter(self, filter_obj):
        # Don't know how to handle Q object yet, but it is probably doable...
        # An unknown type object that supports 'add_to_query' is a different story :)
        if isinstance(filter_obj, models.Q) or hasattr(filter_obj, 'add_to_query'):
            raise NotImplementedError()
        
        newargs, newkwargs = self._translate_args_kwargs(**filter_obj)
        return super(TranslationQueryset, self)._filter_or_exclude(None, *newargs, **newkwargs)

    def annotate(self, *args, **kwargs):
        raise NotImplementedError()

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        fieldnames = self._translate_fieldnames(field_names)
        return super(TranslationQueryset, self).order_by(*fieldnames)
    
    def reverse(self):
        return super(TranslationQueryset, self).reverse()

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
            '_fallback_manager': self._fallback_manager,
            '_forced_unique_fields': self._forced_unique_fields[:],
        })
        if klass:
            klass = self._get_class(klass)
        else:
            klass = self.__class__
        return super(TranslationQueryset, self)._clone(klass, setup, **kwargs)
    
    def iterator(self):
        """
        If this queryset is not filtered by a language code yet, it should be
        filtered first by calling self.language.
        
        If someone doesn't want a queryset filtered by language, they should use
        Model.objects.untranslated()
        """
        if not self._language_code:
            for obj in self.language().iterator():
                yield obj
        else:
            if self._forced_unique_fields:
                # In order for select_related to properly load data from
                # translated models, we have to force django to treat
                # certain fields as one-to-one relations
                # before this queryset calls get_cached_row()
                # We change it back so that things get reset to normal
                # before execution returns to user code.
                # It would be more direct and robust if we could wrap
                # django.db.models.query.get_cached_row() instead, but that's not a class
                # method, sadly, so we cannot override it just for this query

                # Enable temporary forced "unique" attribute for related translated models:
                for field in self._forced_unique_fields:
                    field._unique = True
                # Pre-fetch all objects:
                objects = [o for o in super(TranslationQueryset, self).iterator()]
                # Disable temporary forced attribute:
                for field in self._forced_unique_fields:
                    field._unique = False

                if type(self.query.select_related) == dict:
                    for obj in objects:
                        self._use_related_translations(obj, self.query.select_related)
            else:
                objects = super(TranslationQueryset, self).iterator()
            for obj in objects:
                # non-cascade-deletion hack:
                if not obj.master:
                    yield obj
                else:
                    yield combine(obj, self.shared_model)

    def _use_related_translations(self, obj, relations_dict, follow_relations=True):
        """
        Ensure that we use cached translations brought in via select_related if
        available. Necessary since the database select_related query caches the
        related translation models in a different place than hvad expects it.
        """
        for related_field_name in relations_dict:
            if related_field_name == "master" and follow_relations:
                self._use_related_translations(obj.master, relations_dict[related_field_name], follow_relations=False)
            else:
                related_obj = getattr(obj, related_field_name)
                if related_obj and hasattr(related_obj._meta, 'translations_cache'):
                    # This is a related translated model included using select_related:
                    # The following is a generic version of
                    # "related_obj.translations_cache = related_obj._translations_cache"
                    trans_rel = getattr(related_obj.__class__, related_obj._meta.translations_accessor)
                    new_cache = getattr(related_obj, trans_rel.related.get_cache_name(), None)
                    setattr(related_obj, related_obj._meta.translations_cache, new_cache)


class TranslationManager(models.Manager):
    """
    Manager class for models with translated fields
    """
    #===========================================================================
    # API 
    #===========================================================================

    queryset_class = TranslationQueryset

    def using_translations(self):
        if not hasattr(self, '_real_manager'):
            self.contribute_real_manager()
        qs = self.queryset_class(self.translations_model, using=self.db, real=self._real_manager)
        if hasattr(self, 'core_filters'):
            qs = qs._next_is_sticky().filter(**(self.core_filters))
        return qs

    def language(self, language_code=None):
        return self.using_translations().language(language_code)

    def untranslated(self):
        return self._fallback_manager.get_query_set()

    #===========================================================================
    # Internals
    #===========================================================================

    @property
    def translations_model(self):
        """
        Get the translations model class
        """
        return self.model._meta.translations_model

    #def get_query_set(self):
    #    """
    #    Make sure that querysets inherit the methods on this manager (chaining)
    #    """
    #    return self.untranslated()
    
    def contribute_to_class(self, model, name):
        super(TranslationManager, self).contribute_to_class(model, name)
        self.name = name
        self.contribute_real_manager()
        self.contribute_fallback_manager()
        
    def contribute_real_manager(self):
        self._real_manager = models.Manager()
        self._real_manager.contribute_to_class(self.model, '_%s' % getattr(self, 'name', 'objects'))
    
    def contribute_fallback_manager(self):
        self._fallback_manager = TranslationFallbackManager()
        self._fallback_manager.contribute_to_class(self.model, '_%s_fallback' % getattr(self, 'name', 'objects'))


#===============================================================================
# Fallbacks
#===============================================================================

class FallbackQueryset(QuerySet):
    '''
    Queryset that tries to load a translated version using fallbacks on a per
    instance basis.
    BEWARE: creates a lot of queries!
    '''
    def __init__(self, *args, **kwargs):
        self._translation_fallbacks = None
        super(FallbackQueryset, self).__init__(*args, **kwargs)
    
    def _get_real_instances(self, base_results):
        """
        The logic for this method was taken from django-polymorphic by Bert
        Constantin (https://github.com/bconstantin/django_polymorphic) and was
        slightly altered to fit the needs of django-nani.
        """
        # get the primary keys of the shared model results
        base_ids = [obj.pk for obj in base_results]
        fallbacks = list(self._translation_fallbacks)
        # get all translations for the fallbacks chosen for those shared models,
        # note that this query is *BIG* and might return a lot of data, but it's
        # arguably faster than running one query for each result or even worse
        # one query per result per language until we find something
        translations_manager = self.model._meta.translations_model.objects
        baseqs = translations_manager.select_related('master')
        translations = baseqs.filter(language_code__in=fallbacks,
                                     master__pk__in=base_ids)
        fallback_objects = defaultdict(dict)
        # turn the results into a dict of dicts with shared model primary key as
        # keys for the first dict and language codes for the second dict
        for obj in translations:
            fallback_objects[obj.master.pk][obj.language_code] = obj
        # iterate over the share dmodel results
        for instance in base_results:
            translation = None
            # find the translation
            for fallback in fallbacks:
                translation = fallback_objects[instance.pk].get(fallback, None)
                if translation is not None:
                    break
            # if we found a translation, yield the combined result
            if translation:
                yield combine(translation, self.model)
            else:
                # otherwise yield the shared instance only
                logger.error("no translation for %s.%s (pk=%s)" % (instance._meta.app_label, instance.__class__.__name__, str(instance.pk)))
                yield instance
        
    def iterator(self):
        """
        The logic for this method was taken from django-polymorphic by Bert
        Constantin (https://github.com/bconstantin/django_polymorphic) and was
        slightly altered to fit the needs of django-nani.
        """
        base_iter = super(FallbackQueryset, self).iterator()

        # only do special stuff when we actually want fallbacks
        if self._translation_fallbacks:
            while True:
                base_result_objects = []
                reached_end = False
                
                # get the next "chunk" of results
                for i in range(CHUNK_SIZE):
                    try:
                        instance = next(base_iter)
                        base_result_objects.append(instance)
                    except StopIteration:
                        reached_end = True
                        break
    
                # "combine" the results with their fallbacks
                real_results = self._get_real_instances(base_result_objects)
                
                # yield em!
                for instance in real_results:
                    yield instance
    
                # get out of the while loop if we're at the end, since this is
                # an iterator, we need to raise StopIteration, not "return".
                if reached_end:
                    raise StopIteration
        else:
            # just iterate over it
            for instance in base_iter:
                yield instance
    
    def use_fallbacks(self, *fallbacks):
        if fallbacks:
            self._translation_fallbacks = fallbacks
        else:
            self._translation_fallbacks = FALLBACK_LANGUAGES 
        return self

    def _clone(self, klass=None, setup=False, **kwargs):
        kwargs.update({
            '_translation_fallbacks': self._translation_fallbacks,
        })
        return super(FallbackQueryset, self)._clone(klass, setup, **kwargs)


class TranslationFallbackManager(models.Manager):
    """
    Manager class for the shared model, without specific translations. Allows
    using `use_fallbacks()` to enable per object language fallback.
    """
    def use_fallbacks(self, *fallbacks):
        return self.get_query_set().use_fallbacks(*fallbacks)
    
    def get_query_set(self):
        qs = FallbackQueryset(self.model, using=self.db)
        return qs


#===============================================================================
# TranslationAware
#===============================================================================


class TranslationAwareQueryset(QuerySet):
    def __init__(self, *args, **kwargs):
        super(TranslationAwareQueryset, self).__init__(*args, **kwargs)
        self._language_code = None
        
    def _translate_args_kwargs(self, *args, **kwargs):
        self.language(self._language_code)
        language_joins = []
        newkwargs = {}
        extra_filters = Q()
        for key, value in kwargs.items():
            newkey, langjoins = translate(key, self.model)
            for langjoin in langjoins:
                if langjoin not in language_joins:
                    language_joins.append(langjoin)
            newkwargs[newkey] = value
        newargs = []
        for q in args:
            new_q, langjoins = self._recurse_q(q)
            newargs.append(new_q)
            for langjoin in langjoins:
                if langjoin not in language_joins:
                    language_joins.append(langjoin)
        for langjoin in language_joins:
            extra_filters &= Q(**{langjoin: self._language_code})
        return newargs, newkwargs, extra_filters

    def _recurse_q(self, q):
        newchildren =  []
        language_joins = []
        for child in q.children:
            if isinstance(child, Q):
                newq = self._recurse_q(child)
                newchildren.append(self._recurse_q(newq))
            else:
                key, value = child
                newkey, langjoins =translate(key, self.model)
                newchildren.append((newkey, value))
                for langjoin in langjoins:
                    if langjoin not in language_joins:
                        language_joins.append(langjoin)
        q.children = newchildren
        return q, language_joins
    
    def _translate_fieldnames(self, fields):
        self.language(self._language_code)
        newfields = []
        extra_filters = Q()
        language_joins = []
        for field in fields:
            newfield, langjoins = translate(field, self.model)
            newfields.append(newfield)
            for langjoin in langjoins:
                if langjoin not in language_joins:
                    language_joins.append(langjoin)
        for langjoin in language_joins:
            extra_filters &= Q(**{langjoin: self._language_code})
        return newfields, extra_filters
    
    #===========================================================================
    # Queryset/Manager API 
    #===========================================================================
        
    def language(self, language_code=None):
        if not language_code:
            language_code = get_language()
        self._language_code = language_code
        return self
    
    def get(self, *args, **kwargs):
        newargs, newkwargs, extra_filters = self._translate_args_kwargs(*args, **kwargs)
        return self._filter_extra(extra_filters).get(*newargs, **newkwargs)

    def filter(self, *args, **kwargs):
        newargs, newkwargs, extra_filters = self._translate_args_kwargs(*args, **kwargs)
        return self._filter_extra(extra_filters).filter(*newargs, **newkwargs)

    def aggregate(self, *args, **kwargs):
        raise NotImplementedError()

    def latest(self, field_name=None):
        extra_filters = Q()
        if field_name:
            field_name, extra_filters = translate(self, field_name)
        return self._filter_extra(extra_filters).latest(field_name)

    def in_bulk(self, id_list):
        raise NotImplementedError()

    def values(self, *fields):
        fields, extra_filters = self._translate_fieldnames(fields)
        return self._filter_extra(extra_filters).values(*fields)

    def values_list(self, *fields, **kwargs):
        fields, extra_filters = self._translate_fieldnames(fields)
        return self._filter_extra(extra_filters).values_list(*fields, **kwargs)

    def dates(self, field_name, kind, order='ASC'):
        raise NotImplementedError()

    def exclude(self, *args, **kwargs):
        newargs, newkwargs, extra_filters = self._translate_args_kwargs(*args, **kwargs)
        return self._exclude_extra(extra_filters).exclude(*newargs, **newkwargs)

    def complex_filter(self, filter_obj):
        # admin calls this with an empy filter_obj sometimes
        if filter_obj == {}:
            return self
        raise NotImplementedError()

    def annotate(self, *args, **kwargs):
        raise NotImplementedError()

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        fieldnames, extra_filters = self._translate_fieldnames(field_names)
        return self._filter_extra(extra_filters).order_by(*fieldnames)
    
    def reverse(self):
        raise NotImplementedError()

    def defer(self, *fields):
        raise NotImplementedError()

    def only(self, *fields):
        raise NotImplementedError()
    
    def _clone(self, klass=None, setup=False, **kwargs):
        kwargs.update({
            '_language_code': self._language_code,
        })
        return super(TranslationAwareQueryset, self)._clone(klass, setup, **kwargs)
    
    def _filter_extra(self, extra_filters):
        qs = super(TranslationAwareQueryset, self).filter(extra_filters)
        return super(TranslationAwareQueryset, qs)

    def _exclude_extra(self, extra_filters):
        qs = super(TranslationAwareQueryset, self).exclude(extra_filters)
        return super(TranslationAwareQueryset, qs)
    

class TranslationAwareManager(models.Manager):
    def language(self, language_code=None):
        return self.get_query_set().language(language_code)
        
    def get_query_set(self):
        qs = TranslationAwareQueryset(self.model, using=self.db)
        return qs


#===============================================================================
# Translations Model Manager
#===============================================================================


class TranslationsModelManager(models.Manager):
    def get_language(self, language):
        return self.get(language_code=language)
