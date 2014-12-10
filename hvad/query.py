import django
from django.db.models import Q
from django.db.models.expressions import ExpressionNode
from django.db.models.sql.where import WhereNode

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


#def expression_children(expression):
#    ''' Recursively visit an expression object, yielding each child in turn.
#        - expression: the expression object to visit
#    '''
#    todo = [expression]
#    while todo:
#        expression = todo.pop()
#        for child in expression.children:
#            yield child
#            if isinstance(child, ExpressionNode):
#                todo.append(child)


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
