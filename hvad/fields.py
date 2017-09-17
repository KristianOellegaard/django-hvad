""" Special model fields to generate translation JOINS and augment related_manager API.
    Internal use only, third-party modules and user code must not import this.
"""
import django
from django.apps import apps
from django.db import models
from django.db.models.expressions import Expression, Col, Value
from django.db.models.fields.related import ForeignObject, ReverseManyToOneDescriptor
from django.utils import translation
from django.utils.functional import cached_property
from hvad.utils import set_cached_translation

__all__ = ()

#===============================================================================
# Field for language joins

class FallbacksConstraint(Expression):
    """ A constraint to be added on a Join clause to keep only relevant language """

    def __init__(self, lha, rha, fallbacks):
        """ Setup the constraint to add fallbacks to lha using rha
            lha         - left-hand alias
            rha         - right-hand alias
            fallbacks   - fallback language codes, most priorized first
        """
        self.lha = lha
        self.rha = rha
        self.fallbacks = fallbacks
        super(FallbacksConstraint, self).__init__()

    def as_sql(self, compiler, connection):
        """ Build SQL for constraint """
        quote = compiler.quote_name_unless_alias

        langcases = [
            'WHEN \'%s\' THEN %d' % (lang, i)
            for i, lang in enumerate(self.fallbacks)
        ]
        langcases.append('ELSE %d' % len(self.fallbacks))
        langcases = ' '.join(langcases)

        return (' '.join((
            '(CASE {rha}.language_code', langcases, 'END)'
            ' < '
            '(CASE {lha}.language_code', langcases, 'END)',
            'OR ({rha}.language_code = {lha}.language_code AND {rha}.id < {lha}.id)',
        )).format(lha=quote(self.lha), rha=quote(self.rha)), [])


class BetterTranslationsField(object):
    """ Abstract field used to inject a self-JOIN for computing fallbacks """

    def __init__(self, translation_fallbacks, master):
        """ Setup the abstract field to add given fallbacks to master model
            translation_fallbacks   - language codes, most priorized first
            master                  - shared model to get fallbacks for
        """
        self._fallbacks = []
        self._master = master
        # Filter out duplicates, while preserving order
        seen = set()
        for lang in translation_fallbacks:
            if lang not in seen:
                seen.add(lang)
                self._fallbacks.append(lang)

    def get_extra_restriction(self, where_class, alias, related_alias):
        """ Add the fallbacks constraint to the self-JOIN """
        return FallbacksConstraint(related_alias, alias, self._fallbacks)

    def get_joining_columns(self):
        """ Tell the ORM to add a single self-JOIN """
        return ((self._master, self._master), )

#===============================================================================
# Field for translation navigation

class LanguageConstraint(Expression):
    """ A constraint to be added on a Join clause to keep only relevant language """

    def __init__(self, col):
        """ Setup the LanguageConstraint to filter on given language_code column """
        assert col.target.column == 'language_code'
        self.col = col
        super(LanguageConstraint, self).__init__()

    def as_sql(self, compiler, connection):
        """ Generate SQL for the language constraint.
            Use the language set by the queryset onto the query object.
            Replace None with current language, providing lazy evaluation of language(None)
        """
        language = compiler.query.language_code or translation.get_language()
        if language == 'all':
            assert hasattr(compiler.query.model._meta, 'shared_model')
            value = Col(compiler.query.get_initial_alias(),
                        compiler.query.model._meta.get_field('language_code'), models.CharField())
        else:
            value = Value(language)

        col_sql, col_params = self.col.as_sql(compiler, connection)
        val_sql, val_params = value.as_sql(compiler, connection)
        return (
            '%s = %s' % (col_sql, val_sql),
            col_params + val_params
        )


class SingleTranslationObject(ForeignObject):
    """ Abstract field that provides single-translation lookup in a query by
        inserting a LanguageRestriction in table JOIN clause.
        Allows delegating translation loading to Django's select_related.
    """
    requires_unique_target = False

    def __init__(self, model, translations_model=None):
        if isinstance(model, str):
            model = apps.get_model(model)
        self.shared_model = model
        if translations_model is None:
            translations_model = model._meta.translations_model
        super(SingleTranslationObject, self).__init__(
            translations_model,
            from_fields=['id'], to_fields=['master'],
            null=True,
            auto_created=True,
            editable=False,
            related_name='+',
            on_delete=models.DO_NOTHING,
        )

    def get_extra_restriction(self, where_class, alias, related_alias):
        """ Inject the LanguageConstraint into the join clause. Actual language
            will be resolved by the constraint itself.
        """
        related_model = self.related_model
        return LanguageConstraint(
            Col(alias, related_model._meta.get_field('language_code'), models.CharField())
        )

    def get_path_info(self):
        """ Mark the field as indirect so most Django automation ignores it """
        path = super(SingleTranslationObject, self).get_path_info()
        return [path[0]._replace(direct=False)]

    def contribute_to_class(self, cls, name, virtual_only=False):
        """ Prevent the field from appearing into the class, we only want it in queries """
        super(SingleTranslationObject, self).contribute_to_class(cls, name, False)
        delattr(cls, self.name)

    def deconstruct(self):
        """ Let the field work nicely with migrations """
        name, path, args, kwargs = super(SingleTranslationObject, self).deconstruct()
        args = (
            "%s.%s" % (self.shared_model._meta.app_label,
                       self.shared_model._meta.object_name),
            kwargs['to'],
        )
        kwargs = {}
        return name, path, args, kwargs

#===============================================================================
# Field for customizing related translation manager

class TranslationsAccessor(ReverseManyToOneDescriptor):
    """ Accessor set on TranslatedFields instance.
        Allows customizing the related manager, adding translation-manipulation methods
    """
    @cached_property
    def related_manager_cls(self):
        cls = super(TranslationsAccessor, self).related_manager_cls
        class RelatedManager(cls):
            """ Manager for translations, used by the translation accessor """

            def prefetch(self, force_reload=False):
                """ Load all translations for a model into the prefetched objects cache.
                    Do nothing if prefetch cache is already loaded, unless force_reload is set
                """
                query_name = self.field.related_query_name()
                try:
                    cache = self.instance._prefetched_objects_cache
                except AttributeError:
                    cache = self.instance._prefetched_objects_cache = {}
                try:
                    qs = cache[query_name]
                except KeyError:
                    qs = cache[query_name] = self.get_queryset()
                else:
                    if force_reload:
                        qs._result_cache = None
                bool(qs)    # force evaluation
            prefetch.alters_data = True

            def activate(self, language):
                """ Make translation in specified language current for the instance
                    - Only available from shared model translations accessor
                    - Load all translations if they were not already loaded
                    - Passing None unloads current translation
                    - Raise a DoesNotExist exception if no translation exist for that language
                """
                if language is None:
                    translation = None
                elif language.__class__ is self.model:
                    if language.master_id is not None and language.master_id != self.instance.pk:
                        raise ValueError('Trying to activate a translation that does not '
                                         'belong to this %s' % (self.instance.__class__.__name__,))
                    translation = language
                else:
                    self.prefetch()
                    try:
                        translation = next(obj for obj in self.all() if obj.language_code == language)
                    except StopIteration:
                        raise self.model.DoesNotExist
                set_cached_translation(self.instance, translation)
            activate.alters_data = True

            @property
            def active(self):
                """ Direct reference to the translation currently cached on instance.
                    Thus, obj.translations.active is equivalent to get_cached_translation(obj)
                """
                instance = self.instance
                return instance._meta.get_field('_hvad_query').get_cached_value(instance, None)

            def get_language(self, language):
                """ Return the translation for given language.
                    Use the prefetch cache if available, otherwise hit the database.
                """
                language = language or translation.get_language()
                qs = self.all()
                if qs._result_cache is not None:
                    try:
                        return next(obj for obj in qs if obj.language_code == language)
                    except StopIteration:
                        raise self.model.DoesNotExist('%r is not translated in %r' %
                                                      (self.instance, language))
                else:
                    return qs.get(language_code=language)

            def all_languages(self):
                """ Return a list of all available languages in db.
                    Use the prefetch cache if available, otherwise hit the database.
                """
                qs = self.all()
                if qs._result_cache is not None:
                    return set(obj.language_code for obj in qs)
                return set(qs.values_list('language_code', flat=True))

        return RelatedManager

class MasterKey(models.ForeignKey):
    """ ForeignKey from translation model to its master.
        Customized to it installs the TranslationsAccessor onto the master model.
    """
    related_accessor_class = TranslationsAccessor
