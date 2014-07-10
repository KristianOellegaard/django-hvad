import django
from django.db import models
from django.db.models import Q
from django.db.models.expressions import ExpressionNode
from django.db.models.sql.constants import QUERY_TERMS
from django.db.models.sql.where import WhereNode


class QueryTranslator(object):
    ''' A stateful query translator, building up a list of language joins,
        translated fields (for reverse translation) and additional related
        queries.

        Supports _clone() the same way Django querysets do, and update() to
        merge in the tracked state from another translator.
    '''
    def __init__(self, model):
        self.model = model
        self._language_joins = set()
        self._reverse_cache = {}
        self._shared_fields = None
        self.related_queries = {}

    def update(self, other):
        ''' Merge in the state of another QueryTranslator '''
        assert self.model is other.model
        self._language_joins.update(other._language_joins)
        self._reverse_cache.update(other._reverse_cache)
        self.related_queries.update(other.related_queries)

    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__
        c = klass(self.model)
        c._language_joins = self._language_joins.copy()
        c._reverse_cache = self._reverse_cache.copy()
        c._shared_fields = self._shared_fields      # shared with parent
        c.related_queries = self.related_queries.copy()
        return c

    @property
    def shared_fields(self):
        if self._shared_fields is None:
            self._shared_fields = tuple(self.model._meta.get_all_field_names())
        return self._shared_fields

    def translate_query(self, path, nullable=False, related=False):
        model = self.model
        bits = path.split('__')
        query_term = bits.pop() if bits[-1] in QUERY_TERMS else None

        for depth, bit in enumerate(bits):
            # STEP 1 -- Resolve the field
            if bit == 'pk': # handle 'pk' alias
                bit = model._meta.pk.name

            if hasattr(model._meta, 'translations_accessor'):
                # current model is a shared model
                try:
                    # is field on the shared model?
                    field, _, direct, _ = model._meta.get_field_by_name.real(bit)
                    translated = False
                except models.FieldDoesNotExist:
                    # nope, get field from translations model
                    field, _, direct, _ = (model._meta.translations_model
                                                ._meta.get_field_by_name(bit))
                    translated = True
            else:
                # current model is a standard model
                field, _, direct, _ = model._meta.get_field_by_name(bit)
                translated = False

            # STEP 2 -- Adjust the path bit to reflect real location of the field
            if depth == 0 and not translated:
                # current model is a translation, target is on shared model
                bits[depth] = 'master__%s' % bit
            elif depth > 0 and translated:
                # current model is shared, target is on translation
                taccessor = model._meta.translations_accessor
                bits[depth] = '%s__%s' % (taccessor, bit)
                self._language_joins.add(
                    ('__'.join(bits[:depth] + [taccessor]), nullable)
                )

            # STEP 3 -- Find out the target of the relation, if it is one
            if direct:  # field is on model
                if field.rel:    # field is a foreign key, follow it
                    target = field.rel.to
                else:            # field is a regular field
                    target = None
            else:       # field is a m2m or reverse fk, follow it
                target = field.model

            # STEP 4 -- Some utility stuff
            if related:
                try:
                    taccessor = target._meta.translations_accessor
                except AttributeError:
                    pass
                else:
                    query = '%s__%s' % ('__'.join(bits[:depth+1]), taccessor)
                    self.related_queries[query] = getattr(target, taccessor).related.field
                    self._language_joins.add((query, True))

            # Raise a helpful exception if query bumps into non-relational fields
            if target is None and depth != len(bits)-1:
                raise ValueError('Found regular field %s in query %s' %
                                ('__'.join(bits[:depth+1]), path))

            # STEP 5 -- move on
            model = target

        result = '__'.join(bits)
        if query_term is None:
            self._reverse_cache[result] = path
        else:
            self._reverse_cache[result] = path[:-len(query_term)-2]
            result = '%s__%s' % (result, query_term)
        return result


    def translate_kwarg(self, key, value):
        if isinstance(value, ExpressionNode):
            for node in expression_children(value):
                if isinstance(node, F):
                    node.name = self.translate_query(node.name)
        return self.translate_query(key), value

    def translate_args_kwargs(self, *args, **kwargs):
        # Translate Q nodes in *args
        for q in args:
            for node, nodelist, index in q_children(q):
                nodelist[index] = self.translate_kwarg(*node)
        # Translate kwargs
        newkwargs = dict(self.translate_kwarg(key, value) for key, value in kwargs.items())
        return args, newkwargs

    def translate_fieldnames(self, fieldnames, ordering=False):
        if ordering:
            result = []
            for name in fieldnames:
                if name == '?':
                    result.append('?')
                    continue
                prefix, name = ('-', name[1:]) if name[0] == '-' else ('', name)
                result.append('%s%s' % (prefix, self.translate_query(name)))
            return tuple(result)
        else:
            return tuple(self.translate_query(key) for key in fieldnames)

    def reverse_translate_fieldnames_dict(self, fieldname_dict):
        """ Translates a translated path back to untranslated form
            Can only translate paths issued from the same query
        """
        result = {}
        for key, value in fieldname_dict.items():
            try: # Most common case for ValuesQuerySet
                result[self._reverse_cache[key]] = value
                continue
            except KeyError:
                pass
            try: # Automatically attributed aggregate aliases
                root, tail = key.rsplit('__', 1)
                result['%s__%s' % (self._reverse_cache[root], tail)] = value
                continue
            except (KeyError, ValueError):
                pass
            # Manually attributed aggregate aliases
            result[key] = value
        return result

    def build_language_filters(self, language):
        filters = []
        for join, nullable in self._language_joins:
            q_object = Q(**{'%s__language_code' % join: language})
            if nullable:
                q_object = q_object | Q(**{'%s__language_code' % join: None})
            filters.append(q_object)
        return filters

#===============================================================================
# Generators abstracting walking through internal django structures

def q_children(q):
    ''' Recursively visit a Q object, yielding each (key, value) pair found.
        - q: the Q object to visit
        - Yields a 3-tuple ((key, value), containing_list, index_in_list) so
          as to allow updating the tuple in the list
    '''
    todo = [q]
    while todo:
        q = todo.pop()
        for index, child in enumerate(q.children):
            if isinstance(child, Q):
                todo.append(child)
            else:
                yield child, q.children, index


def expression_children(expression):
    ''' Recursively visit an expression object, yielding each child in turn.
        - expression: the expression object to visit
    '''
    todo = [expression]
    while todo:
        expression = todo.pop()
        for child in expression.children:
            yield child
            if isinstance(child, ExpressionNode):
                todo.append(child)


def where_node_children(node):
    ''' Recursively visit all children of a where node, yielding each field in turn.
        - node: the node to visit
    '''
    todo = [node]
    get_field_name = ((lambda n: n.lhs.target.name) if django.VERSION >= (1, 7) else
                      (lambda n: n[0].field.name))
    while todo:
        node = todo.pop()
        for child in node.children:
            try:
                field_name = get_field_name(child)
            except (TypeError, AttributeError):
                pass
            else:
                yield child, field_name
            if isinstance(child, WhereNode):
                todo.append(child)
