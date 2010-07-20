# -*- coding: utf-8 -*-
"""
    sphinx.util.docfields
    ~~~~~~~~~~~~~~~~~~~~~

    "Doc fields" are reST field lists in object descriptions that will
    be domain-specifically transformed to a more appealing presentation.

    :copyright: Copyright 2007-2010 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes

from sphinx import addnodes


def _is_single_paragraph(node):
    """True if the node only contains one paragraph (and system messages)."""
    if len(node) == 0:
        return False
    elif len(node) > 1:
        for subnode in node[1:]:
            if not isinstance(subnode, nodes.system_message):
                return False
    if isinstance(node[0], nodes.paragraph):
        return True
    return False


class Field(object):
    """
    A doc field that is never grouped.  It can have an argument or not, the
    argument can be linked using a specified *rolename*.  Field should be used
    for doc fields that usually don't occur more than once.

    Example::

       :returns: description of the return value
       :rtype: description of the return type
    """
    is_grouped = False
    is_typed = False

    def __init__(self, name, names=(), label=None, has_arg=True, rolename=None):
        self.name = name
        self.names = names
        self.label = label
        self.has_arg = has_arg
        self.rolename = rolename

    def make_xref(self, rolename, domain, target, innernode=nodes.emphasis):
        if not rolename:
            return innernode(target, target)
        refnode = addnodes.pending_xref('', refdomain=domain, refexplicit=False,
                                        reftype=rolename, reftarget=target)
        refnode += innernode(target, target)
        return refnode

    def make_entry(self, fieldarg, content):
        return (fieldarg, content)

    def make_field(self, types, domain, item):
        fieldarg, content = item
        fieldname = nodes.field_name('', self.label)
        if fieldarg:
            fieldname += nodes.Text(' ')
            fieldname += self.make_xref(self.rolename, domain,
                                        fieldarg, nodes.Text)
        fieldbody = nodes.field_body('', nodes.paragraph('', '', *content))
        return nodes.field('', fieldname, fieldbody)


class GroupedField(Field):
    """
    A doc field that is grouped; i.e., all fields of that type will be
    transformed into one field with its body being a bulleted list.  It always
    has an argument.  The argument can be linked using the given *rolename*.
    GroupedField should be used for doc fields that can occur more than once.
    If *can_collapse* is true, this field will revert to a Field if only used
    once.

    Example::

       :raises ErrorClass: description when it is raised
    """
    is_grouped = True
    list_type = nodes.bullet_list

    def __init__(self, name, names=(), label=None, rolename=None,
                 can_collapse=False):
        Field.__init__(self, name, names, label, True, rolename)
        self.can_collapse = can_collapse

    def make_field(self, types, domain, items):
        fieldname = nodes.field_name('', self.label)
        listnode = self.list_type()
        if len(items) == 1 and self.can_collapse:
            return Field.make_field(self, types, domain, items[0])
        for fieldarg, content in items:
            par = nodes.paragraph()
            par += self.make_xref(self.rolename, domain, fieldarg, nodes.strong)
            par += nodes.Text(' -- ')
            par += content
            listnode += nodes.list_item('', par)
        fieldbody = nodes.field_body('', listnode)
        return nodes.field('', fieldname, fieldbody)


class TypedField(GroupedField):
    """
    A doc field that is grouped and has type information for the arguments.  It
    always has an argument.  The argument can be linked using the given
    *rolename*, the type using the given *typerolename*.

    Two uses are possible: either parameter and type description are given
    separately, using a field from *names* and one from *typenames*,
    respectively, or both are given using a field from *names*, see the example.

    Example::

       :param foo: description of parameter foo
       :type foo:  SomeClass

       -- or --

       :param SomeClass foo: description of parameter foo
    """
    is_typed = True

    def __init__(self, name, names=(), typenames=(), label=None,
                 rolename=None, typerolename=None):
        GroupedField.__init__(self, name, names, label, rolename, False)
        self.typenames = typenames
        self.typerolename = typerolename

    def make_field(self, types, domain, items):
        fieldname = nodes.field_name('', self.label)
        listnode = self.list_type()
        for fieldarg, content in items:
            par = nodes.paragraph()
            par += self.make_xref(self.rolename, domain, fieldarg, nodes.strong)
            if fieldarg in types:
                typename = u''.join(n.astext() for n in types[fieldarg])
                par += nodes.Text(' (')
                par += self.make_xref(self.typerolename, domain, typename)
                par += nodes.Text(')')
            par += nodes.Text(' -- ')
            par += content
            listnode += nodes.list_item('', par)
        fieldbody = nodes.field_body('', listnode)
        return nodes.field('', fieldname, fieldbody)


class DocFieldTransformer(object):
    """
    Transforms field lists in "doc field" syntax into better-looking
    equivalents, using the field type definitions given on a domain.
    """

    def __init__(self, directive):
        self.domain = directive.domain
        if not hasattr(directive, '_doc_field_type_map'):
            directive.__class__._doc_field_type_map = \
                self.preprocess_fieldtypes(directive.__class__.doc_field_types)
        self.typemap = directive._doc_field_type_map

    def preprocess_fieldtypes(self, types):
        typemap = {}
        for fieldtype in types:
            for name in fieldtype.names:
                typemap[name] = fieldtype, False
            if fieldtype.is_typed:
                for name in fieldtype.typenames:
                    typemap[name] = fieldtype, True
        return typemap

    def transform_all(self, node):
        """Transform all field list children of a node."""
        # don't traverse, only handle field lists that are immediate children
        for child in node:
            if isinstance(child, nodes.field_list):
                self.transform(child)

    def transform(self, node):
        """Transform a single field list *node*."""
        typemap = self.typemap

        entries = []
        groupindices = {}
        types = {}

        # step 1: traverse all fields and collect field types and content
        for field in node:
            fieldname, fieldbody = field
            try:
                # split into field type and argument
                fieldtype, fieldarg = fieldname.astext().split(None, 1)
            except ValueError:
                # maybe an argument-less field type?
                fieldtype, fieldarg = fieldname.astext(), ''
            typedesc, is_typefield = typemap.get(fieldtype, (None, None))

            # sort out unknown fields
            if typedesc is None or typedesc.has_arg != bool(fieldarg):
                # either the field name is unknown, or the argument doesn't
                # match the spec; capitalize field name and be done with it
                new_fieldname = fieldtype.capitalize() + ' ' + fieldarg
                fieldname[0] = nodes.Text(new_fieldname)
                entries.append(field)
                continue

            typename = typedesc.name

            # collect the content, trying not to keep unnecessary paragraphs
            if _is_single_paragraph(fieldbody):
                content = fieldbody.children[0].children
            else:
                content = fieldbody.children

            # if the field specifies a type, put it in the types collection
            if is_typefield:
                # filter out only inline nodes; others will result in invalid
                # markup being written out
                content = filter(
                    lambda n: isinstance(n, nodes.Inline) or isinstance(n, nodes.Text),
                    content)
                if content:
                    types.setdefault(typename, {})[fieldarg] = content
                continue

            # also support syntax like ``:param type name:``
            if typedesc.is_typed:
                try:
                    argtype, argname = fieldarg.split(None, 1)
                except ValueError:
                    pass
                else:
                    types.setdefault(typename, {})[argname] = \
                                               [nodes.Text(argtype)]
                    fieldarg = argname

            # grouped entries need to be collected in one entry, while others
            # get one entry per field
            if typedesc.is_grouped:
                if typename in groupindices:
                    group = entries[groupindices[typename]]
                else:
                    groupindices[typename] = len(entries)
                    group = [typedesc, []]
                    entries.append(group)
                group[1].append(typedesc.make_entry(fieldarg, content))
            else:
                entries.append([typedesc,
                                typedesc.make_entry(fieldarg, content)])

        # step 2: all entries are collected, construct the new field list
        new_list = nodes.field_list()
        for entry in entries:
            if isinstance(entry, nodes.field):
                # pass-through old field
                new_list += entry
            else:
                fieldtype, content = entry
                fieldtypes = types.get(fieldtype.name, {})
                new_list += fieldtype.make_field(fieldtypes, self.domain,
                                                 content)

        node.replace_self(new_list)
