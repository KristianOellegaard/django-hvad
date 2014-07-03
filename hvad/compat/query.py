import django

if django.VERSION >= (1, 7):
    def get_where_node_field_name(node):
        return node.lhs.target.name
else:
    def get_where_node_field_name(node):
        return node[0].field.name
