from collections import defaultdict
import django
from django.conf import settings
from django.core.exceptions import FieldError
from django.db import models, transaction, IntegrityError
if django.VERSION >= (1, 9):
    from django.db.models.query import QuerySet
elif django.VERSION >= (1, 8):
    from django.db.models.query import QuerySet, ValuesQuerySet
else:
    from django.db.models.query import QuerySet, ValuesQuerySet, DateQuerySet, DateTimeQuerySet
if django.VERSION >= (1, 8):
    from django.db.models.sql.datastructures import Join, LOUTER
from django.db.models.sql.constants import GET_ITERATOR_CHUNK_SIZE as CHUNK_SIZE
from django.db.models import F, Q
from django.utils.translation import get_language
from hvad.compat import string_types
from hvad.query import (query_terms, q_children, expression_nodes, where_node_children,
                        add_alias_constraints)
from hvad.utils import combine, minimumDjangoVersion, settings_updater
from copy import deepcopy
import logging
import sys
import warnings

#===============================================================================

# Logging-related globals
_logger = logging.getLogger(__name__)

# Global settings, wrapped so they react to SettingsOverride
@settings_updater
def update_settings(*args, **kwargs):
    global FALLBACK_LANGUAGES, LEGACY_FALLBACKS
    FALLBACK_LANGUAGES = tuple(code for code, name in settings.LANGUAGES)
    LEGACY_FALLBACKS = bool(getattr(settings, 'HVAD_LEGACY_FALLBACKS', False))

#===============================================================================

class FieldTranslator(object):
    """
    Translates *shared* field names from '<shared_field>' to
    'master__<shared_field>' and caches those names.
    """
    def __init__(self, manager):
        self._manager = manager
        if django.VERSION >= (1, 8):
            fields = set()
            for field in manager.shared_model._meta.get_fields():
                fields.add(field.name)
                if hasattr(field, 'attname'):
                    fields.add(field.attname)
            fields.add('pk')
            self._shared_fields = tuple(fields)
        else:
            self._shared_fields = tuple(manager.shared_model._meta.get_all_field_names()) + ('pk',)
        self._cache = dict()
        super(FieldTranslator, self).__init__()

    def __call__(self, key):
        try:
            ret = self._cache[key]
        except KeyError:
            ret = self._build(key)
            self._cache[key] = ret
        return ret

    def _build(self, key):
        """
        Checks if the selected field is a shared field
        and in that case, prefixes it with master___
        It also handles - and ? in case its called by
        order_by()
        """
        if key == "?":
            return key
        if key.startswith("-"):
            prefix, key = "-", key[1:]
        else:
            prefix = ""
        if key.startswith(self._shared_fields):
            return '%smaster__%s' % (prefix, key)
        else:
            return '%s%s' % (prefix, key)

#===============================================================================

if django.VERSION >= (1, 9):
    from django.db.models.query import ValuesIterable, ValuesListIterable, FlatValuesListIterable
    class TranslatedValuesIterable(ValuesIterable):
        def __iter__(self):
            queryset = self.queryset
            for row in super(TranslatedValuesIterable, self).__iter__():
                yield queryset._reverse_translate_fieldnames_dict(row)

    iterable_overrides = {
        ValuesIterable: TranslatedValuesIterable,
        ValuesListIterable: ValuesListIterable,
        FlatValuesListIterable: FlatValuesListIterable,
    }

else:
    class ValuesMixin(object):
        _skip_master_select = True

        def iterator(self):
            qs = self._clone()._add_language_filter()
            for row in super(ValuesMixin, qs).iterator():
                if isinstance(row, dict):
                    yield qs._reverse_translate_fieldnames_dict(row)
                else:
                    yield row

    class SkipMasterSelectMixin(object):
        _skip_master_select = True

#===============================================================================

class ForcedUniqueFields(object):
    """ Context manager that forces a set of fields to be unique while active """
    def __init__(self, fields):
        self.fields = fields

    def __enter__(self):
        for field in self.fields:
            field._unique = True

    def __exit__(self, *args):
        for field in self.fields:
            field._unique = False

#===============================================================================
# Field for language joins
#===============================================================================

class RawConstraint(object):
    def __init__(self, sql, aliases):
        self.sql = sql
        self.aliases = aliases

    def as_sql(self, qn, connection):
        aliases = tuple(qn(alias) for alias in self.aliases)
        return (self.sql % aliases, [])

class BetterTranslationsField(object):
    def __init__(self, translation_fallbacks, master):
        # Filter out duplicates, while preserving order
        self._fallbacks = []
        self._master = master
        seen = set()
        for lang in translation_fallbacks:
            if lang not in seen:
                seen.add(lang)
                self._fallbacks.append(lang)

    def get_extra_restriction(self, where_class, alias, related_alias):
        langcase = ('(CASE %s.language_code ' +
                    ' '.join('WHEN \'%s\' THEN %d' % (lang, i)
                             for i, lang in enumerate(self._fallbacks)) +
                    ' ELSE %d END)' % len(self._fallbacks))
        return RawConstraint(
            sql=' '.join((langcase, '<', langcase, 'OR ('
                          '%s.language_code = %s.language_code AND '
                          '%s.id < %s.id)')),
            aliases=(alias, related_alias,
                     alias, related_alias,
                     alias, related_alias)
        )

    @minimumDjangoVersion(1, 8)
    def get_joining_columns(self):
        return ((self._master, self._master), )

#===============================================================================
# TranslationQueryset
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
    override_classes = {}
    if django.VERSION < (1, 9):
        override_classes[ValuesQuerySet] = ValuesMixin
    if django.VERSION < (1, 8):
        override_classes[DateQuerySet] = SkipMasterSelectMixin
        override_classes[DateTimeQuerySet] = SkipMasterSelectMixin
    _skip_master_select = False

    def __init__(self, *args, **kwargs):
        # model can be either first positional, or a named arg
        if len(args) >= 1:
            model, args = args[0], args[1:]
        else:
            model = kwargs.pop('model', None)

        if model is not None:  # check the given model is correct
            if hasattr(model._meta, 'translations_model'):
                # normal creation gets a shared model that we must flip around
                model, self.shared_model = model._meta.translations_model, model
            elif not hasattr(model._meta, 'shared_model'):
                raise TypeError('TranslationQueryset only works on translatable models')

        self._local_field_names = None
        self._field_translator = None
        self._language_code = None
        self._language_fallbacks = None
        self._raw_select_related = []
        self._forced_unique_fields = []  # Used for select_related
        self._language_filter_tag = False
        self._hvad_switch_fields = ()
        super(TranslationQueryset, self).__init__(model, *args, **kwargs)

    #===========================================================================
    # Helpers and properties (INTERNAL!)
    #===========================================================================

    def _clone(self, klass=None, setup=False, **kwargs):
        """ Creates a clone of this queryset - Django equivalent of copy()
        This method keeps all defining attributes and drops data caches
        """
        kwargs.update({
            'shared_model': self.shared_model,
            '_local_field_names': self._local_field_names,
            '_field_translator': self._field_translator,
            '_language_code': self._language_code,
            '_language_fallbacks': self._language_fallbacks,
            '_raw_select_related': self._raw_select_related,
            '_forced_unique_fields': list(self._forced_unique_fields),
            '_language_filter_tag': getattr(self, '_language_filter_tag', False),
            '_hvad_switch_fields': self._hvad_switch_fields,
        })
        if django.VERSION < (1, 9):
            kwargs.update({
                'klass': None if klass is None else self._get_class(klass),
                'setup': setup,
            })
        return super(TranslationQueryset, self)._clone(**kwargs)

    @property
    def field_translator(self):
        if self._field_translator is None:
            self._field_translator = FieldTranslator(self)
        return self._field_translator

    @property
    def shared_local_field_names(self):
        if self._local_field_names is None:
            if django.VERSION >= (1, 8):
                fields = set()
                for field in self.shared_model._meta.get_fields():
                    fields.add(field.name)
                    if hasattr(field, 'attname'):
                        fields.add(field.attname)
                self._local_field_names = tuple(fields)
            else:
                self._local_field_names = self.shared_model._meta.get_all_field_names()
        return self._local_field_names

    def _translate_args_kwargs(self, *args, **kwargs):
        # Translate args (Q objects) from '<shared_field>' to
        # 'master__<shared_field>' where necessary.
        newargs = deepcopy(args)
        for q in newargs:
            for child, children, index in q_children(q):
                children[index] = (self.field_translator(child[0]), child[1])
        # Translated kwargs from '<shared_field>' to 'master__<shared_field>'
        # where necessary.
        newkwargs = dict((self.field_translator(key), value)
                         for key, value in kwargs.items())
        return newargs, newkwargs

    def _translate_expression(self, expr):
        if isinstance(expr, string_types):
            return self.field_translator(expr)
        for node in expression_nodes(expr):
            if isinstance(node, F):
                node.name = self.field_translator(node.name)
            elif hasattr(node, 'lookup'):
                node.lookup = self.field_translator(node.lookup)
        return expr

    def _translate_fieldnames(self, fieldnames):
        return [self.field_translator(name) for name in fieldnames]

    def _reverse_translate_fieldnames_dict(self, fieldname_dict):
        """
        Helper function to make sure the user doesnt get "bothered"
        with the construction of shared/translated model

        Translates e.g.
        {'master__number_avg': 10} to {'number__avg': 10}

        """
        prefix = 'master__'
        return dict(
            (key[len(prefix):] if key.startswith(prefix) else key, value)
            for key, value in fieldname_dict.items()
        )

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
        else: # pragma: no cover
            return klass

    def _get_shared_queryset(self):
        qs = super(TranslationQueryset, self)._clone()
        qs.__class__ = QuerySet
        accessor = self.shared_model._meta.translations_accessor
        # update using the real manager
        return QuerySet(self.shared_model, using=self.db).filter(**{'%s__in' % accessor: qs})

    def _add_select_related(self, language_code):
        fields = self._raw_select_related
        related_queries = []
        language_filters = []
        force_unique_fields = []
        if not self._skip_master_select and getattr(self, '_fields', None) is None:
            related_queries.append('master')

        for query_key in fields:
            newbits = []
            for term in query_terms(self.shared_model, query_key):

                # Translate term
                if term.depth == 0 and not term.translated:
                    # on initial depth we must key to shared model
                    newbits.append('master__%s' % term.term)
                elif term.depth > 0 and term.translated:
                    # on deeper levels we must key to translations model
                    # this will work because translations will be seen as _unique
                    # at query time
                    newbits.append('%s__%s' % (term.model._meta.translations_accessor, term.term))
                else:
                    newbits.append(term.term)

                # Some helpful messages for common mistakes
                if term.many:
                    raise FieldError('Cannot select_related: %s can be multiple objects. '
                                     'Use prefetch_related instead.' % query_key)
                if term.target is None:
                    raise FieldError('Cannot select_related: %s is a regular field' % query_key)
                if hasattr(term.field.rel, 'through'):
                    raise FieldError('Cannot select_related: %s can be multiple objects. '
                                     'Use prefetch_related instead.' % query_key)

                # If target is a translated model, select its translations
                target_translations = getattr(term.target._meta, 'translations_accessor', None)
                if target_translations is not None:
                    # Add the model
                    target_query = '__'.join(newbits)
                    related_queries.append('%s__%s' % (target_query, target_translations))

                    # Add a language filter for the translation
                    language_filters.append('%s__%s__language_code' % (
                        target_query,
                        target_translations,
                    ))

                    # Remember to mark the field unique so JOIN is generated
                    # and row decoder gets cached items
                    if django.VERSION >= (1, 9):
                        target_transfield = getattr(term.target, target_translations).field
                    else:
                        target_transfield = getattr(term.target, target_translations).related.field
                    force_unique_fields.append(target_transfield)

            related_queries.append('__'.join(newbits))

        # Apply results to query
        self.query.add_select_related(related_queries)
        for language_filter in language_filters:
            self.query.add_q(Q(**{language_filter: language_code}) |
                             Q(**{language_filter: None}))

        self._forced_unique_fields = force_unique_fields

    def _add_language_filter(self):
        if self._language_filter_tag: # pragma: no cover
            raise RuntimeError('Queryset is already tagged. This is a bug in hvad')
        self._language_filter_tag = True

        if self._language_code == 'all':
            self._add_select_related(F('language_code'))

        elif self._language_fallbacks:
            if self._raw_select_related:
                raise NotImplementedError('Using select_related along with '
                                          'fallbacks() is not supported')
            languages = tuple(get_language() if lang is None else lang
                              for lang in (self._language_code,) + self._language_fallbacks)

            if django.VERSION >= (1, 8):
                masteratt = self.model._meta.get_field('master').attname
                alias = self.query.join(Join(
                    self.model._meta.db_table,
                    self.query.get_initial_alias(),
                    None,
                    LOUTER,
                    BetterTranslationsField(languages, master=masteratt),
                    True
                ))
            else:
                masteratt = self.model._meta.get_field('master').attname
                nullable = ({'nullable': True} if django.VERSION >= (1, 7) else
                            {'nullable': True, 'outer_if_first': True})
                alias = self.query.join((self.query.get_initial_alias(), self.model._meta.db_table,
                                        ((masteratt, masteratt),)),
                                        join_field=BetterTranslationsField(languages, master=masteratt),
                                        **nullable)

            add_alias_constraints(self, (self.model, alias), id__isnull=True)
            self.query.add_filter(('%s__isnull' % masteratt, False))
            if not self._skip_master_select and getattr(self, '_fields', None) is None:
                self.query.add_select_related(('master',))

        else:
            language_code = self._language_code or get_language()
            for _, field_name in where_node_children(self.query.where):
                if field_name == 'language_code':
                    # remove in 1.4
                    raise RuntimeError(
                        'Overriding language_code in get() or filter() is no longer supported. '
                        'Please set the language in Model.objects.language() instead, '
                        'or use language("all") to do manual filtering on languages.')
            else:
                self.query.add_filter(('language_code', language_code))
            self._add_select_related(language_code)

        # if queryset is about to use the model's default ordering, we
        # override that now with a translated version of the model's ordering
        if self.query.default_ordering and not self.query.order_by:
            ordering = self.shared_model._meta.ordering
            self.query.order_by = self._translate_fieldnames(ordering or [])

        return self

    def _use_related_translations(self, obj, relations_dict, depth=0):
        """
        Ensure that we use cached translations brought in via select_related if
        available. Necessary since the database select_related query caches the
        related translation models in a different place than hvad expects it.
        """

        # First, set translation for current object,
        accessor = getattr(obj._meta, 'translations_accessor', None)
        if accessor is not None:
            if django.VERSION >= (1, 9):
                cache = getattr(obj.__class__, accessor).rel.get_cache_name()
            else:
                cache = getattr(obj.__class__, accessor).related.get_cache_name()
            try:
                translation = getattr(obj, cache)
            except AttributeError:
                pass
            else:
                delattr(obj, cache)
                setattr(obj, obj._meta.translations_cache, translation)

        # Then recurse in the relation dict
        for field, sub_dict in relations_dict.items():
            target = translation if field == accessor else getattr(obj, field)
            if target is not None:
                self._use_related_translations(target, sub_dict, depth+1)


    #===========================================================================
    # Queryset/Manager API
    #===========================================================================

    def language(self, language_code=None):
        self._language_code = language_code
        return self

    def fallbacks(self, *fallbacks):
        if not fallbacks:
            self._language_fallbacks = FALLBACK_LANGUAGES
        elif fallbacks == (None,):
            self._language_fallbacks = None
        else:
            self._language_fallbacks = fallbacks
        return self

    #===========================================================================
    # Queryset/Manager API that do database queries
    #===========================================================================

    def iterator(self):
        """
        If this queryset is not filtered by a language code yet, it should be
        filtered first by calling self.language.

        If someone doesn't want a queryset filtered by language, they should use
        Model.objects.untranslated()
        """
        qs = self._clone()._add_language_filter()
        qs._known_related_objects = {}  # super's iterator will attempt to set them

        if django.VERSION >= (1, 9) and qs._iterable_class in iterable_overrides:
            qs._iterable_class = iterable_overrides[qs._iterable_class]
            for obj in super(TranslationQueryset, qs).iterator():
                yield obj
            return

        if qs._forced_unique_fields:
            # HACK: In order for select_related to properly load data from
            # translated models, we have to force django to treat
            # certain fields as one-to-one relations
            # before this queryset calls get_cached_row()
            # We change it back so that things get reset to normal
            # before execution returns to user code.
            # It would be more direct and robust if we could wrap
            # django.db.models.query.get_cached_row() instead, but that's not a class
            # method, sadly, so we cannot override it just for this query

            with ForcedUniqueFields(qs._forced_unique_fields):
                # Pre-fetch all objects:
                objects = list(super(TranslationQueryset, qs).iterator())

            if type(qs.query.select_related) == dict:
                for obj in objects:
                    qs._use_related_translations(obj, qs.query.select_related)
        else:
            objects = super(TranslationQueryset, qs).iterator()

        for obj in objects:
            # non-cascade-deletion hack:
            if not obj.master:
                yield obj
            else:
                for name in self._hvad_switch_fields:
                    try:
                        setattr(obj.master, name, getattr(obj, name))
                    except AttributeError: # pragma: no cover
                        pass
                    else:
                        delattr(obj, name)
                obj = combine(obj, qs.shared_model)
                # use known objects from self, not qs as we cleared it earlier
                for field, rel_objs in self._known_related_objects.items():
                    if hasattr(obj, field.get_cache_name()):
                        # should not happen, but we conform to Django behavior
                        continue #pragma: no cover
                    pk = getattr(obj, field.get_attname())
                    try:
                        rel_obj = rel_objs[pk]
                    except KeyError: #pragma: no cover
                        pass
                    else:
                        setattr(obj, field.name, rel_obj)
                yield obj

    def create(self, **kwargs):
        if 'language_code' in kwargs:
            if self._language_code is not None:
                # remove in 1.4
                raise RuntimeError('Overriding language_code in create() is no longer allowed. '
                                   'Please set the language with language() instead.')
        else:
            kwargs['language_code'] = self._language_code or get_language()
        if kwargs['language_code'] == 'all':
            raise ValueError('Cannot create an object with language \'all\'')
        obj = self.shared_model(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db)
        return obj

    def count(self):
        if self._result_cache is None:
            qs = self._clone()._add_language_filter()
            return super(TranslationQueryset, qs).count()
        else:
            return len(self._result_cache)

    def exists(self):
        if self._result_cache is None:
            qs = self._clone()._add_language_filter()
            return super(TranslationQueryset, qs).exists()
        else:
            return bool(self._result_cache)

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
            pass

        params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
        params.update(defaults)

        if 'language_code' in params:
            if self._language_code is not None:
                # remove in 1.4
                raise RuntimeError('Overriding language_code in get_or_create() is no longer allowed. '
                                   'Please set the language in Model.objects.language() instead.')
        else:
            params['language_code'] = self._language_code or get_language()
        if params['language_code'] == 'all':
            raise ValueError('Cannot create an object with language \'all\'')

        obj = self.shared_model(**params)
        try:
            with transaction.atomic(using=self.db):
                obj.save(force_insert=True, using=self.db)
            return obj, True
        except IntegrityError:
            exc_info = sys.exc_info()
            try:
                return self.get(**lookup), False
            except self.model.DoesNotExist:
                raise exc_info[1]

    @minimumDjangoVersion(1, 7)
    def update_or_create(self, defaults=None, **kwargs):
        raise NotImplementedError()

    def bulk_create(self, objs, batch_size=None):
        raise NotImplementedError()

    def aggregate(self, *args, **kwargs):
        """
        Loops over all the passed aggregates and translates the fieldnames
        """
        qs = self._clone()._add_language_filter()
        newargs = tuple(qs._translate_expression(item) for item in args)
        newkwargs = dict(
            (k, qs._translate_expression(v)) for k, v in kwargs.items()
        )
        response = super(TranslationQueryset, qs).aggregate(*newargs, **newkwargs)
        return qs._reverse_translate_fieldnames_dict(response)

    def latest(self, field_name=None):
        field_name = self.field_translator(field_name or self.shared_model._meta.get_latest_by)
        return super(TranslationQueryset, self).latest(field_name)

    def earliest(self, field_name=None):
        field_name = self.field_translator(field_name or self.shared_model._meta.get_latest_by)
        return super(TranslationQueryset, self).earliest(field_name)

    def in_bulk(self, id_list):
        if not id_list:
            return {}
        if self._language_code == 'all':
            raise ValueError('Cannot use in_bulk along with language(\'all\').')
        qs = self.filter(pk__in=id_list)
        qs.query.clear_ordering(force_empty=True)
        return dict((obj._get_pk_val(), obj) for obj in qs.iterator())

    def delete(self):
        qs = self._get_shared_queryset()
        qs.delete()
    delete.alters_data = True
    delete.queryset_only = True

    def delete_translations(self):
        self.update(master=None)
        self.model.objects.filter(master__isnull=True).delete()
    delete_translations.alters_data = True

    def update(self, **kwargs):
        qs = self._clone()._add_language_filter()
        shared, translated = qs._split_kwargs(**kwargs)
        count = 0
        if translated:
            count += super(TranslationQueryset, qs).update(**translated)
        if shared:
            shared_qs = qs._get_shared_queryset()
            count += shared_qs.update(**shared)
        return count
    update.alters_data = True

    #===========================================================================
    # Queryset/Manager API that return another queryset
    #===========================================================================

    def filter(self, *args, **kwargs):
        if 'language_code' in kwargs and kwargs['language_code'] == 'all':
            raise ValueError('Value "all" is invalid for language_code')
        newargs, newkwargs = self._translate_args_kwargs(*args, **kwargs)
        return super(TranslationQueryset, self).filter(*newargs, **newkwargs)

    def exclude(self, *args, **kwargs):
        if 'language_code' in kwargs and kwargs['language_code'] == 'all':
            raise ValueError('Value "all" is invalid for language_code')
        newargs, newkwargs = self._translate_args_kwargs(*args, **kwargs)
        return super(TranslationQueryset, self).exclude(*newargs, **newkwargs)

    def extra(self, select=None, where=None, params=None, tables=None,
              order_by=None, select_params=None):
        qs = super(TranslationQueryset, self).extra(select, where, params, tables,
                                                    order_by, select_params)
        if select:
            switch_fields = set(self._hvad_switch_fields)
            switch_fields.update(select.keys())
            qs._hvad_switch_fields = tuple(switch_fields)
        return qs

    def values(self, *fields):
        fields = self._translate_fieldnames(fields)
        return super(TranslationQueryset, self).values(*fields)

    def values_list(self, *fields, **kwargs):
        fields = self._translate_fieldnames(fields)
        return super(TranslationQueryset, self).values_list(*fields, **kwargs)

    def dates(self, field_name, kind=None, order='ASC'):
        if django.VERSION < (1, 8):
            field_name = self.field_translator(field_name)
        return super(TranslationQueryset, self).dates(field_name, kind=kind, order=order)

    def datetimes(self, field, *args, **kwargs):
        if django.VERSION < (1, 8):
            field = self.field_translator(field)
        return super(TranslationQueryset, self).datetimes(field, *args, **kwargs)

    def select_related(self, *fields):
        if not fields:
            raise NotImplementedError('To use select_related on a translated model, '
                                      'you must provide a list of fields.')
        if fields == (None,):
            self._raw_select_related = []
        elif django.VERSION >= (1, 7):  # in newer versions, calls are cumulative
            self._raw_select_related.extend(fields)
        else:  #pragma: no cover        # in older versions, they overwrite each other
            self._raw_select_related = list(fields)
        return self

    def complex_filter(self, filter_obj):
        # Don't know how to handle Q object yet, but it is probably doable...
        # An unknown type object that supports 'add_to_query' is a different story :)
        if isinstance(filter_obj, models.Q) or hasattr(filter_obj, 'add_to_query'):
            raise NotImplementedError()

        newargs, newkwargs = self._translate_args_kwargs(**filter_obj)
        return super(TranslationQueryset, self)._filter_or_exclude(None, *newargs, **newkwargs)

    def annotate(self, *args, **kwargs):
        newkwargs = dict((k, self._translate_expression(v)) for k, v in kwargs.items())
        for arg in args:
            arg = self._translate_expression(arg)
            try:
                alias = arg.default_alias
            except (AttributeError, TypeError):
                raise TypeError("Complex annotations require an alias")
            if alias.startswith('master__'):
               alias = alias[8:]
            if alias in kwargs:
                raise ValueError("The named annotation '%s' conflicts with the "
                                 "default name for another annotation." % alias)
            newkwargs[alias] = arg

        qs = super(TranslationQueryset, self).annotate(**newkwargs)

        switch_fields = set(qs._hvad_switch_fields)
        switch_fields.update(newkwargs)
        qs._hvad_switch_fields = tuple(switch_fields)
        return qs

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

#===============================================================================
# Fallbacks
#===============================================================================

class _SharedFallbackQueryset(QuerySet):
    translation_fallbacks = None

    def use_fallbacks(self, *fallbacks):
        if django.VERSION >= (1, 9):
            raise AssertionError(
                'TranslationManager.untranslated().use_fallbacks() is not supported on Django 1.9, '
                'and is deprecated on previous versions as well. Please use the fallbacks() method '
                'on queryset instead, eg: MyModel.objects.language().fallbacks()')
        warnings.warn('TranslationManager.untranslated().use_fallbacks() is deprecated. '
                      'Please use the fallbacks() method on queryset instead, eg: '
                      'MyModel.objects.language().fallbacks()', DeprecationWarning, stacklevel=2)
        self.translation_fallbacks = fallbacks or (None,)+FALLBACK_LANGUAGES
        return self

    def _clone(self, klass=None, setup=False, **kwargs):
        kwargs.update({
            'translation_fallbacks': self.translation_fallbacks,
        })
        if django.VERSION < (1, 9):
            kwargs.update({'klass': klass, 'setup': setup})
        return super(_SharedFallbackQueryset, self)._clone(**kwargs)

    def aggregate(self, *args, **kwargs):
        raise NotImplementedError()

    def annotate(self, *args, **kwargs):
        raise NotImplementedError()

    def defer(self, *args, **kwargs):
        raise NotImplementedError()

    def only(self, *args, **kwargs):
        raise NotImplementedError()


class LegacyFallbackQueryset(_SharedFallbackQueryset): #pragma: no cover
    '''
    Queryset that tries to load a translated version using fallbacks on a per
    instance basis.
    BEWARE: creates a lot of queries!
    '''
    def _get_real_instances(self, base_results):
        """
        The logic for this method was taken from django-polymorphic by Bert
        Constantin (https://github.com/bconstantin/django_polymorphic) and was
        slightly altered to fit the needs of django-hvad.
        """
        # get the primary keys of the shared model results
        base_ids = [obj.pk for obj in base_results]
        fallbacks = [get_language() if lang is None else lang
                     for lang in self.translation_fallbacks]
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
                _logger.error("no translation for %s.%s (pk=%s)" %
                              (instance._meta.app_label,
                               instance.__class__.__name__,
                               str(instance.pk)))
                yield instance

    def iterator(self):
        """
        The logic for this method was taken from django-polymorphic by Bert
        Constantin (https://github.com/bconstantin/django_polymorphic) and was
        slightly altered to fit the needs of django-hvad.
        """
        base_iter = super(LegacyFallbackQueryset, self).iterator()

        # only do special stuff when we actually want fallbacks
        if self.translation_fallbacks:
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

class SelfJoinFallbackQueryset(_SharedFallbackQueryset):
    def iterator(self):
        # only do special stuff when we actually want fallbacks
        if self.translation_fallbacks:
            fallbacks = [get_language() if lang is None else lang
                         for lang in self.translation_fallbacks]
            tmodel = self.model._meta.translations_model
            taccessor = self.model._meta.translations_accessor
            taccessorcache = (
                getattr(self.model, taccessor).rel.get_cache_name() if django.VERSION >= (1, 9) else
                getattr(self.model, taccessor).related.get_cache_name()
            )
            tcache = self.model._meta.translations_cache
            masteratt = tmodel._meta.get_field('master').attname
            field = BetterTranslationsField(fallbacks, master=masteratt)

            qs = self._clone()

            qs.query.add_select_related((taccessor,))
            # This join will be reused by the select_related. We must provide it
            # anyway because the order matters and add_select_related does not
            # populate joins right away.
            if django.VERSION >= (1, 8):
                alias1 = qs.query.join(Join(
                    tmodel._meta.db_table,
                    qs.query.get_initial_alias(),
                    None,
                    LOUTER,
                    getattr(qs.model, taccessor).field.rel if django.VERSION >= (1, 9) else
                    getattr(qs.model, taccessor).related.field.rel,
                    True
                ))
                alias2 = qs.query.join(Join(
                    tmodel._meta.db_table,
                    alias1,
                    None,
                    LOUTER,
                    field,
                    True
                ))
            else:
                nullable = ({'nullable': True} if django.VERSION >= (1, 7) else
                            {'nullable': True, 'outer_if_first': True})
                alias1 = qs.query.join((qs.query.get_initial_alias(), tmodel._meta.db_table,
                                        ((qs.model._meta.pk.attname, masteratt),)),
                                    join_field=getattr(qs.model, taccessor).related.field.rel,
                                    **nullable)
                alias2 = qs.query.join((tmodel._meta.db_table, tmodel._meta.db_table,
                                        ((masteratt, masteratt),)),
                                    join_field=field, **nullable)

            add_alias_constraints(qs, (tmodel, alias2), id__isnull=True)

            # We must force the _unique field so get_cached_row populates the cache
            # Unfortunately, this means we must load everything in one go
            related_field = (getattr(qs.model, taccessor).field if django.VERSION >= (1, 9) else
                             getattr(qs.model, taccessor).related.field)
            with ForcedUniqueFields([related_field]):
                objects = []
                for instance in super(SelfJoinFallbackQueryset, qs).iterator():
                    try:
                        translation = getattr(instance, taccessorcache)
                    except AttributeError: #pragma: no cover
                        _logger.error("no translation for %s.%s (pk=%s)",
                                    instance._meta.app_label,
                                    instance.__class__.__name__,
                                    str(instance.pk))
                    else:
                        setattr(instance, tcache, translation)
                        delattr(instance, taccessorcache)
                    objects.append(instance)
            return iter(objects)
        else:
            return super(SelfJoinFallbackQueryset, self).iterator()


FallbackQueryset = LegacyFallbackQueryset if LEGACY_FALLBACKS else SelfJoinFallbackQueryset


#===============================================================================
# TranslationManager
#===============================================================================


class TranslationManager(models.Manager):
    """
    Manager class for models with translated fields
    """
    #===========================================================================
    # API
    #===========================================================================
    use_for_related_fields = True

    queryset_class = TranslationQueryset
    fallback_class = FallbackQueryset
    default_class = QuerySet

    def __init__(self, *args, **kwargs):
        self.queryset_class = kwargs.pop('queryset_class', self.queryset_class)
        self.fallback_class = kwargs.pop('fallback_class', self.fallback_class)
        self.default_class = kwargs.pop('default_class', self.default_class)
        super(TranslationManager, self).__init__(*args, **kwargs)

    def _make_queryset(self, klass, core_filters):
        ''' Builds a queryset of given class.
            core_filters tells whether the queryset will bypass RelatedManager
            mechanics and therefore needs to reapply the filters on its own.
        '''
        if django.VERSION >= (1, 7):
            qs = klass(self.model, using=self.db, hints=self._hints)
        else:
            qs = klass(self.model, using=self.db) #pragma: no cover
        core_filters = getattr(self, 'core_filters', None) if core_filters else None
        if core_filters:
            qs = qs._next_is_sticky().filter(**core_filters)
        return qs

    def language(self, language_code=None):
        return self._make_queryset(self.queryset_class, True).language(language_code)

    def untranslated(self):
        return self._make_queryset(self.fallback_class, True)

    def get_queryset(self):
        return self._make_queryset(self.default_class, False)

    #===========================================================================
    # Internals
    #===========================================================================

    @property
    def translations_model(self):
        return self.model._meta.translations_model


#===============================================================================
# TranslationAware
#===============================================================================


class TranslationAwareQueryset(QuerySet):
    def __init__(self, *args, **kwargs):
        super(TranslationAwareQueryset, self).__init__(*args, **kwargs)
        self._language_code = None

    def _translate(self, key, model, language_joins):
        ''' Translate a key on a model.
            language_joins must be a set that will be updated with required
            language joins for given key
        '''
        newkey = []
        for term in query_terms(model, key):
            if term.translated:
                newkey.append('%s__%s' % (term.model._meta.translations_accessor, term.term))
            else:
                newkey.append(term.term)
            if term.target is not None:
                taccessor = getattr(term.target._meta, 'translations_accessor', None)
                if taccessor is not None:
                    language_joins.add('__'.join(newkey + [taccessor, 'language_code']))
        return '__'.join(newkey)

    def _translate_args_kwargs(self, *args, **kwargs):
        self.language(self._language_code)
        language_joins = set()
        extra_filters = Q()
        newkwargs = dict(
            (self._translate(key, self.model, language_joins), value)
            for key, value in kwargs.items()
        )
        newargs = deepcopy(args)
        for q in newargs:
            for child, children, index in q_children(q):
                children[index] = (self._translate(child[0], self.model, language_joins),
                                   child[1])
        for langjoin in language_joins:
            extra_filters &= Q(**{langjoin: self._language_code})
        return newargs, newkwargs, extra_filters

    def _translate_fieldnames(self, fields):
        self.language(self._language_code)
        extra_filters = Q()
        language_joins = set()
        newfields = tuple(
            self._translate(field, self.model, language_joins)
            for field in fields
        )

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
        extra = Q()
        if field_name:
            language_joins, lang = set(), self._language_code or get_language()
            field_name = self._translate(field_name, self.model, language_joins)
            for join in language_joins:
                extra &= Q(**{join: lang})
        return self._filter_extra(extra).latest(field_name)

    def earliest(self, field_name=None):
        extra = Q()
        if field_name:
            language_joins, lang = set(), self._language_code or get_language()
            field_name = self._translate(field_name, self.model, language_joins)
            for join in language_joins:
                extra &= Q(**{join: lang})
        return self._filter_extra(extra).earliest(field_name)

    def in_bulk(self, id_list):
        if not id_list:
            return {}
        qs = self.filter(pk__in=id_list)
        qs.query.clear_ordering(force_empty=True)
        return dict((obj._get_pk_val(), obj) for obj in qs.iterator())

    def values(self, *fields):
        fields, extra_filters = self._translate_fieldnames(fields)
        return self._filter_extra(extra_filters).values(*fields)

    def values_list(self, *fields, **kwargs):
        fields, extra_filters = self._translate_fieldnames(fields)
        return self._filter_extra(extra_filters).values_list(*fields, **kwargs)

    def dates(self, field_name, kind, order='ASC'):
        raise NotImplementedError()

    def datetimes(self, field, *args, **kwargs):
        raise NotImplementedError()

    def exclude(self, *args, **kwargs):
        newargs, newkwargs, extra_filters = self._translate_args_kwargs(*args, **kwargs)
        if extra_filters.children:
            combined = extra_filters & ~Q(*args, **kwargs)
            return super(TranslationAwareQueryset, self).filter(combined)
        else:
            return super(TranslationAwareQueryset, self).exclude(*newargs, **newkwargs)

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
        if django.VERSION < (1, 9):
            kwargs.update({'klass': klass, 'setup': setup})
        return super(TranslationAwareQueryset, self)._clone(**kwargs)

    def _filter_extra(self, extra_filters):
        if extra_filters.children:
            qs = self._next_is_sticky()
            qs = super(TranslationAwareQueryset, qs).filter(extra_filters)
        else:
            qs = self
        return super(TranslationAwareQueryset, qs)


class TranslationAwareManager(models.Manager):
    def language(self, language_code=None):
        return self.get_queryset().language(language_code)

    def get_queryset(self):
        qs = TranslationAwareQueryset(self.model, using=self.db)
        return qs

#===============================================================================
# Translations Model Manager
#===============================================================================


class TranslationsModelManager(models.Manager):
    def get_language(self, language):
        qs = self.all()
        if qs._result_cache is None:
            return self.get(language_code=language)
        else: # take advantage of cached translations
            for obj in qs:
                if obj.language_code == language:
                    return obj
        raise self.model.DoesNotExist
