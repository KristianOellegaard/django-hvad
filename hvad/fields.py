from django.apps import apps
from django.db import models
from django.db.models.expressions import Expression, Col, Value
from django.db.models.fields.related import ForeignObject
from django.utils import translation

__all__ = ()

#===============================================================================
# Field for language joins
#===============================================================================

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
        """ Add the fallbacks constraint to the self-JOIN """
        return FallbacksConstraint(related_alias, alias, self._fallbacks)

    def get_joining_columns(self):
        """ Tell the ORM to add a single self-JOIN """
        return ((self._master, self._master), )

#===============================================================================
# Field for translation navigation
#===============================================================================

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

    def get_cache_name(self):
        """ Have select_related store loaded translation right into translation cache """
        return self.shared_model._meta.translations_cache

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
