# -*- coding: utf-8 -*-
from django.core.exceptions import FieldError
from django.db.models.fields import FieldDoesNotExist, DateField
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.sql.datastructures import Date
from django.db.models.sql.query import Query
from nani.manager import TranslationQueryset

class DateQuerySet(TranslationQueryset):
    def iterator(self):
        return self.query.get_compiler(self.db).results_iter()

    def _setup_query(self):
        """
        Sets up any special features of the query attribute.

        Called by the _clone() method after initializing the rest of the
        instance.
        """
        self.query.clear_deferred_loading()
        self.query = self.query.clone(klass=DateQuery, setup=True)
        self.query.select = []
        self.query.add_date_select(self._field_name, self._kind, self._order)

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(DateQuerySet, self)._clone(klass, False, **kwargs)
        c._field_name = self._field_name
        c._kind = self._kind
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c


class DateQuery(Query):
    """
    A DateQuery is a normal query, except that it specifically selects a single
    date field. This requires some special handling when converting the results
    back to Python objects, so we put it in a separate class.
    """

    compiler = 'SQLDateCompiler'

    def add_date_select(self, field_name, lookup_type, order='ASC'):
        """
        Converts the query into a date extraction query.
        """
        try:
            result = self.setup_joins(
                field_name.split(LOOKUP_SEP),
                self.get_meta(),
                self.get_initial_alias(),
                False
            )
        except FieldError:
            raise FieldDoesNotExist("%s has no field named '%s'" % (
                self.model._meta.object_name, field_name
            ))
        field = result[0]
        assert isinstance(field, DateField), "%r isn't a DateField." \
                % field.name
        alias = result[3][-1]
        select = Date((alias, field.column), lookup_type)
        self.select = [select]
        self.select_fields = [None]
        self.select_related = False # See #7097.
        self.set_extra_mask([])
        self.distinct = True
        self.order_by = order == 'ASC' and [1] or [-1]

        if field.null:
            self.add_filter(("%s__isnull" % field_name, False))