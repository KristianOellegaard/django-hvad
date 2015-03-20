#################
:mod:`hvad.query`
#################

.. module:: hvad.query

This modules containts abstractions for accessing some internal parts of Django
ORM that are used in hvad. The intent is that anytime some code in hvad needs
to access some Django internals, it should do so through a function in this module.

.. function:: query_terms(model, path)

    This iterator yields all terms in the specified ``path``, along with full
    introspection data. Each term is output as a named tuple with the following
    members:

    * ``depth``:  how deep in the path is this term. Counted from zero.
    * ``term``: the term string.
    * ``model: `` the model the term is attached to. It will start with passed
      ``model`` then walk through relations as terms are enumerated.
    * ``field``: the actual field, on the model, the term refers to.
    * ``translated``: whether the field is a translated field (True) or a shared fielf (False).
    * ``target``: the target model of the relation, or ``None`` if not a relational field.
    * ``many``: whether the target can be multiple (that is, it is a M2M or reverse FK).

    If a field is not recognized, it is assumed the path is complete and everything
    that follows is a query expression (such as ``__year__in``). Query expression
    terms will be yielded with ``field`` set to ``None``.

.. function:: q_children(q)

    Iterator that recursively yields all key-value pairs of a ``Q`` object. Each
    pair is yielded as a 3-tuple: the pair itself, its container and its index in
    the container. This allows modifying it.

.. function:: expression_nodes(expression)

    Iterator that recursively yields all nodes in an expression tree.

.. function:: where_node_children(node)

    Iterator that recursively yields all fields of a where node. It is used to
    determine whether a custom ``Q`` object included a ``language_code`` filter.
