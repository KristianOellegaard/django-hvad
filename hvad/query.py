import django
from django.db.models import Q, FieldDoesNotExist
from django.db.models.expressions import Expression, Col
from django.db.models.sql.where import AND
from collections import namedtuple

__all__ = ()

#===============================================================================
# Generators abstracting walking through internal django structures

QueryTerm = namedtuple('QueryTerm', 'depth term model field translated target many')

def query_terms(model, path):
    """ Yields QueryTerms of given path starting from given model.
        - model can be either a regular model or a translatable model
    """
    bits = path.split('__')
    field = None
    for depth, bit in enumerate(bits):
        # STEP 1 -- Resolve the field
        if bit == 'pk': # handle 'pk' alias
            bit = model._meta.pk.name

        try:
            try:                        # is field on the shared model?
                field = model._meta.get_field.real(bit)
                translated = False
            except FieldDoesNotExist:   # nope, get field from translations model
                field = model._meta.translations_model._meta.get_field(bit)
                translated = True
            except AttributeError:      # current model is a standard model
                field = model._meta.get_field(bit)
                translated = False
            direct = (
                not field.auto_created or
                getattr(field, 'db_column', None) or
                getattr(field, 'attname', None)
            )
        except FieldDoesNotExist:
            break


        # STEP 2 -- Find out the target of the relation, if it is one
        if direct:  # field is on model
            if django.VERSION >= (1, 9):
                if field.remote_field:      # field is a foreign key, follow it
                    target = field.remote_field.model._meta.concrete_model
                else:
                    target = None           # field is a regular field
            else:
                if field.rel:               # field is a foreign key, follow it
                    target = field.rel.to._meta.concrete_model
                else:
                    target = None           # field is a regular field
        else:       # field is a m2m or reverse fk, follow it
            target = field.related_model._meta.concrete_model

        yield QueryTerm(
            depth=depth,
            term=bit,
            model=model,
            field=field,
            translated=translated,
            target=target,
            many=not direct
        )

        # Onto next iteration
        if target is None:
            depth += 1   # we hit a regular field, mark it as yielded then break
            break        # through to lookup/transform flushing
        model = target

    else:
        return  # all bits were recognized as fields, job done

    # STEP 3 -- Flush lookup/transform bits - do not handle invalid stuff, Django will do it
    for depth, bit in enumerate(bits[depth:], depth):
        yield QueryTerm(
            depth=depth,
            term=bit,
            model=model,
            field=None,
            translated=None,
            target=None,
            many=False
        )


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

def expression_nodes(expression):
    ''' Recursively visit an expression object, yielding each node in turn.
        - expression: the expression object to visit
    '''
    todo = [expression]
    while todo:
        expression = todo.pop()
        if expression is not None:
            yield expression
        if isinstance(expression, Expression):
            todo.extend(expression.get_source_expressions())

#===============================================================================
# Query manipulations

def add_alias_constraints(queryset, alias, **kwargs):
    model, alias = alias
    clause = queryset.query.where_class()
    for lookup, value in kwargs.items():
        field_name, lookup = lookup.split('__')
        clause.add(queryset.query.build_lookup(
            [lookup],
            Col(alias, model._meta.get_field(field_name)),
            value
        ), AND)
    queryset.query.where.add(clause, AND)
