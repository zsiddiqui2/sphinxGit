# -*- coding: utf-8 -*-
"""
    sphinx.writers.texinfo
    ~~~~~~~~~~~~~~~~~~~~~~

    Custom docutils writer for Texinfo.

    :copyright: Copyright 2007-2011 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from os import path

from docutils import nodes, writers

from sphinx import addnodes
from sphinx.locale import versionlabels


TEMPLATE = """\
\\input texinfo   @c -*-texinfo-*-
@c %%**start of header
@setfilename %(filename)s
@documentencoding UTF-8
@copying
Generated by Sphinx
@end copying
@settitle %(title)s
@defindex ge
@paragraphindent %(paragraphindent)s
@exampleindent %(exampleindent)s
@afourlatex
%(direntry)s
@c %%**end of header

@titlepage
@title %(title)s
@author %(author)s
@end titlepage
@contents

@c %%** start of user preamble
%(preamble)s
@c %%** end of user preamble

@ifnottex
@node Top
@top %(title)s
@end ifnottex

@c %%**start of body
%(body)s
@c %%**end of body
@bye
"""


def find_subsections(section):
    """Return a list of subsections for the given ``section``."""
    result = []
    for child in section.children:
        if isinstance(child, nodes.section):
            result.append(child)
            continue
        result.extend(find_subsections(child))
    return result


## Escaping
# Which characters to escape depends on the context.  In some cases,
# namely menus and node names, it's not possible to escape certain
# characters.

def escape(s):
    """Return a string with Texinfo command characters escaped."""
    s = s.replace('@', '@@')
    s = s.replace('{', '@{')
    s = s.replace('}', '@}')
    # Prevent "--" from being converted to an "em dash"
    # s = s.replace('-', '@w{-}')
    return s

def escape_arg(s):
    """Return an escaped string suitable for use as an argument
    to a Texinfo command."""
    s = escape(s)
    # Commas are the argument delimeters
    s = s.replace(',', '@comma{}')
    # Normalize white space
    s = ' '.join(s.split()).strip()
    return s

def escape_id(s):
    """Return an escaped string suitable for node names, menu entries,
    and xrefs anchors."""
    bad_chars = ',:.()@{}'
    for bc in bad_chars:
        s = s.replace(bc, ' ')
    s = ' '.join(s.split()).strip()
    return s

class TexinfoWriter(writers.Writer):
    """Texinfo writer for generating Texinfo documents."""
    supported = ('texinfo', 'texi')

    settings_spec = (
        'Texinfo Specific Options',
        None,
        (
            ("Name of the resulting Info file to be created by 'makeinfo'.  "
             "Should probably end with '.info'.",
             ['--texinfo-filename'],
             {'default': '', 'metavar': '<file>'}),

            ('Specify the Info dir entry category.',
             ['--texinfo-dir-category'],
             {'default': 'Miscellaneous', 'metavar': '<name>'}),

            ('The name to use for the Info dir entry.  '
             'If not provided, no entry will be created.',
             ['--texinfo-dir-entry'],
             {'default': '', 'metavar': '<name>'}),

            ('A brief description (one or two lines) to use for the '
             'Info dir entry.',
             ['--texinfo-dir-description'],
             {'default': '', 'metavar': '<desc>'}),
            )
        )

    settings_defaults = {}
    settings_default_overrides = {'docinfo_xform': 0}

    output = None

    visitor_attributes = ('output', 'fragment')

    def __init__(self, builder):
        writers.Writer.__init__(self)
        self.builder = builder

    def translate(self):
        self.visitor = visitor = TexinfoTranslator(self.document, self.builder)
        self.document.walkabout(visitor)
        visitor.finish()
        for attr in self.visitor_attributes:
            setattr(self, attr, getattr(visitor, attr))


class TexinfoTranslator(nodes.NodeVisitor):

    ignore_missing_images = False

    default_elements = {
        'filename': '',
        'title': '',
        'paragraphindent': 2,
        'exampleindent': 4,
        'direntry': '',
        'preamble': '',
        'body': '',
        }

    def __init__(self, document, builder):
        nodes.NodeVisitor.__init__(self, document)
        self.builder = builder
        self.init_settings()

        self.written_ids = set()    # node names and anchors in output
        self.referenced_ids = set() # node names and anchors that should
                                    # be in output
        self.node_names = {}  # node name --> node's name to display
        self.node_menus = {}  # node name --> node's menu entries
        self.rellinks = {}    # node name --> (next, previous, up)

        self.collect_node_names()
        self.collect_node_menus()
        self.collect_rellinks()

        self.short_ids = {}
        self.body = []
        self.context = []
        self.previous_section = None
        self.section_level = 0
        self.seen_title = False
        self.next_section_targets = []
        self.escape_newlines = 0
        self.curfilestack = []

    def finish(self):
        while self.referenced_ids:
            # Handle xrefs with missing anchors
            r = self.referenced_ids.pop()
            if r not in self.written_ids:
                self.document.reporter.info(
                    "Unknown cross-reference target: `%s'" % r)
                self.add_text('@anchor{%s}@w{%s}\n' % (r, ' ' * 30))
        self.fragment = ''.join(self.body).strip() + '\n'
        self.elements['body'] = self.fragment
        self.output = TEMPLATE % self.elements


    ## Helper routines

    def init_settings(self):
        settings = self.settings = self.document.settings
        elements = self.elements = self.default_elements.copy()
        elements.update({
                # if empty, the title is set to the first section title
                'title': settings.title,
                'author': escape_arg(settings.author),
                # if empty, use basename of input file
                'filename': settings.texinfo_filename,
                })
        # Title
        title = elements['title']
        if not title:
            title = self.document.next_node(nodes.title)
            title = (title and title.astext()) or '<untitled>'
        elements['title'] = escape_id(title) or '<untitled>'
        # Filename
        if not elements['filename']:
            elements['filename'] = self.document.get('source') or 'untitled'
            if elements['filename'][-4:] in ('.txt', '.rst'):
                elements['filename'] = elements['filename'][:-4]
            elements['filename'] += '.info'
        # Direntry
        if settings.texinfo_dir_entry:
            elements['direntry'] = ('@dircategory %s\n'
                                    '@direntry\n'
                                    '* %s: (%s).    %s\n'
                                    '@end direntry\n') % (
                escape_id(settings.texinfo_dir_category),
                escape_id(settings.texinfo_dir_entry),
                elements['filename'],
                escape_arg(settings.texinfo_dir_description))
        # allow the user to override them all
        elements.update(settings.texinfo_elements)

    def collect_node_names(self):
        """Generates a unique id for each section.

        Assigns the attribute ``node_name`` to each section."""
        self.document['node_name'] = 'Top'
        self.node_names['Top'] = 'Top'
        self.written_ids.update(('Top', 'top'))

        for section in self.document.traverse(nodes.section):
            title = section.next_node(nodes.Titular)
            name = (title and title.astext()) or '<untitled>'
            node_id = name = escape_id(name) or '<untitled>'
            assert node_id and name
            nth, suffix = 1, ''
            while (node_id + suffix).lower() in self.written_ids:
                nth += 1
                suffix = '<%s>' % nth
            node_id += suffix
            assert node_id not in self.node_names
            assert node_id not in self.written_ids
            assert node_id.lower() not in self.written_ids
            section['node_name'] = node_id
            self.node_names[node_id] = name
            self.written_ids.update((node_id, node_id.lower()))

    def collect_node_menus(self):
        """Collect the menu entries for each "node" section."""
        node_menus = self.node_menus
        for node in ([self.document] +
                     self.document.traverse(nodes.section)):
            assert 'node_name' in node and node['node_name']
            entries = tuple(s['node_name']
                            for s in find_subsections(node))
            node_menus[node['node_name']] = entries
        # Try to find a suitable "Top" node
        title = self.document.next_node(nodes.title)
        top = (title and title.parent) or self.document
        if not isinstance(top, (nodes.document, nodes.section)):
            top = self.document
        if top is not self.document:
            entries = node_menus[top['node_name']]
            entries += node_menus['Top'][1:]
            node_menus['Top'] = entries
            del node_menus[top['node_name']]
            top['node_name'] = 'Top'

    def collect_rellinks(self):
        """Collect the relative links (next, previous, up) for each "node"."""
        rellinks = self.rellinks
        node_menus = self.node_menus
        for id, entries in node_menus.items():
            rellinks[id] = ['', '', '']
        # Up's
        for id, entries in node_menus.items():
            for e in entries:
                rellinks[e][2] = id
        # Next's and prev's
        for id, entries in node_menus.items():
            for i, id in enumerate(entries):
                # First child's prev is empty
                if i != 0:
                    rellinks[id][1] = entries[i-1]
                # Last child's next is empty
                if i != len(entries) - 1:
                    rellinks[id][0] = entries[i+1]
        # Top's next is its first child
        try:
            first = node_menus['Top'][0]
        except IndexError:
            pass
        else:
            rellinks['Top'][0] = first
            rellinks[first][1] = 'Top'

    def add_text(self, text, fresh=False):
        """Add some text to the output.

        Optional argument ``fresh`` means to insert a newline before
        the text if the last character out was not a newline."""
        if fresh:
            if self.body and not self.body[-1].endswith('\n'):
                self.body.append('\n')
        self.body.append(text)

    def rstrip(self):
        """Strip trailing whitespace from the current output."""
        while self.body and not self.body[-1].strip():
            del self.body[-1]
        if not self.body:
            return
        self.body[-1] = self.body[-1].rstrip()

    def add_menu_entries(self, entries):
        for entry in entries:
            name = self.node_names[entry]
            if name == entry:
                self.add_text('* %s::\n' % name, fresh=1)
            else:
                self.add_text('* %s: %s.\n' % (name, entry), fresh=1)

    def add_menu(self, node_name):
        entries = self.node_menus[node_name]
        if not entries:
            return
        self.add_text('\n@menu\n')
        self.add_menu_entries(entries)
        if node_name != 'Top':
            self.rstrip()
            self.add_text('\n@end menu\n')
            return

        def _add_detailed_menu(name):
            entries = self.node_menus[name]
            if not entries:
                return
            self.add_text('\n%s\n\n' % (self.node_names[name],))
            self.add_menu_entries(entries)
            for subentry in entries:
                _add_detailed_menu(subentry)

        self.add_text('\n@detailmenu\n'
                      ' --- The Detailed Node Listing ---\n')
        for entry in entries:
            _add_detailed_menu(entry)
        self.rstrip()
        self.add_text('\n@end detailmenu\n'
                      '@end menu\n')

    def tex_image_length(self, width_str):
        match = re.match('(\d*\.?\d*)\s*(\S*)', width_str)
        if not match:
            # fallback
            return width_str
        res = width_str
        amount, unit = match.groups()[:2]
        if not unit or unit == "px":
            # pixels: let TeX alone
            return ''
        elif unit == "%":
            # a4paper: textwidth=418.25368pt
            res = "%d.0pt" % (float(amount) * 4.1825368)
        return res

    ## xref handling

    def get_short_id(self, id):
        """Return a shorter 'id' associated with ``id``."""
        # Shorter ids improve paragraph filling in places
        # that the id is hidden by Emacs.
        try:
            sid = self.short_ids[id]
        except KeyError:
            sid = hex(len(self.short_ids))[2:]
            self.short_ids[id] = sid
        return sid

    def add_anchor(self, id, msg_node=None):
        # Anchors can be referenced by their original id
        # or by the generated shortened id
        id = escape_id(id).lower()
        ids = (self.get_short_id(id), id)
        for id in ids:
            if id not in self.written_ids:
                self.add_text('@anchor{%s}' % id)
                self.written_ids.add(id)

    def add_xref(self, ref, name, node):
        ref = self.get_short_id(escape_id(ref).lower())
        name = ' '.join(name.split()).strip()
        if not name or ref == name:
            self.add_text('@pxref{%s}' % ref)
        else:
            self.add_text('@pxref{%s,,%s}' % (ref, name))
        self.referenced_ids.add(ref)

    ## Visiting

    def visit_document(self, node):
        pass
    def depart_document(self, node):
        pass

    def visit_Text(self, node):
        s = escape(node.astext())
        if self.escape_newlines:
            s = s.replace('\n', ' ')
        self.add_text(s)
    def depart_Text(self, node):
        pass

    def visit_section(self, node):
        self.next_section_targets.extend(node.get('ids', []))
        if not self.seen_title:
            return
        if self.previous_section:
            self.add_menu(self.previous_section['node_name'])
        else:
            self.add_menu('Top')

        node_name = node['node_name']
        pointers = tuple([node_name] + self.rellinks[node_name])
        self.add_text('\n@node %s,%s,%s,%s\n' % pointers)
        if node_name != node_name.lower():
            self.add_text('@anchor{%s}' % node_name.lower())
        for id in self.next_section_targets:
            self.add_anchor(id, node)

        self.next_section_targets = []
        self.previous_section = node
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    headings = (
        '@unnumbered',
        '@chapter',
        '@section',
        '@subsection',
        '@subsubsection',
        )

    rubrics = (
        '@heading',
        '@subheading',
        '@subsubheading',
        )

    def visit_title(self, node):
        if not self.seen_title:
            self.seen_title = 1
            raise nodes.SkipNode
        parent = node.parent
        if isinstance(parent, nodes.table):
            return
        if isinstance(parent, nodes.Admonition):
            raise nodes.SkipNode
        elif isinstance(parent, nodes.sidebar):
            self.visit_rubric(node)
        elif isinstance(parent, nodes.topic):
            raise nodes.SkipNode
        elif not isinstance(parent, nodes.section):
            self.document.reporter.warning(
                'encountered title node not in section, topic, table, '
                'admonition or sidebar', base_node=node)
            self.visit_rubric(node)
        else:
            try:
                heading = self.headings[self.section_level]
            except IndexError:
                heading = self.headings[-1]
            self.add_text('%s ' % heading, fresh=1)

    def depart_title(self, node):
        self.add_text('', fresh=1)

    def visit_rubric(self, node):
        try:
            rubric = self.rubrics[self.section_level]
        except IndexError:
            rubric = self.rubrics[-1]
        self.add_text('%s ' % rubric, fresh=1)
    def depart_rubric(self, node):
        self.add_text('', fresh=1)

    def visit_subtitle(self, node):
        self.add_text('\n\n@noindent\n')
    def depart_subtitle(self, node):
        self.add_text('\n\n')

    ## References

    def visit_target(self, node):
        if node.get('ids'):
            self.add_anchor(node['ids'][0], node)
        elif node.get('refid'):
            # Section targets need to go after the start of the section.
            next = node.next_node(ascend=1, siblings=1)
            while isinstance(next, nodes.target):
                next = next.next_node(ascend=1, siblings=1)
            if isinstance(next, nodes.section):
                self.next_section_targets.append(node['refid'])
                return
            self.add_anchor(node['refid'], node)
        elif node.get('refuri'):
            pass
        else:
            self.document.reporter.error("Unknown target type: %r" % node)

    def visit_reference(self, node):
        if isinstance(node.parent, nodes.title):
            return
        if isinstance(node[0], nodes.image):
            return
        if isinstance(node.parent, addnodes.desc_type):
            return
        name = node.get('name', node.astext()).strip()
        if node.get('refid'):
            self.add_xref(escape_id(node['refid']),
                          escape_id(name), node)
            raise nodes.SkipNode
        if not node.get('refuri'):
            self.document.reporter.error("Unknown reference type: %s" % node)
            return
        uri = node['refuri']
        if uri.startswith('#'):
            self.add_xref(escape_id(uri[1:]), escape_id(name), node)
        elif uri.startswith('%'):
            id = uri[1:]
            if '#' in id:
                src, id = uri[1:].split('#', 1)
            assert '#' not in id
            self.add_xref(escape_id(id), escape_id(name), node)
        elif uri.startswith('mailto:'):
            uri = escape_arg(uri[7:])
            name = escape_arg(name)
            if not name or name == uri:
                self.add_text('@email{%s}' % uri)
            else:
                self.add_text('@email{%s,%s}' % (uri, name))
        elif uri.startswith('info:'):
            uri = uri[5:].replace('_', ' ')
            uri = escape_arg(uri)
            id = 'Top'
            if '#' in uri:
                uri, id = uri.split('#', 1)
            id = escape_id(id)
            name = escape_id(name)
            if name == id:
                self.add_text('@pxref{%s,,,%s}' % (id, uri))
            else:
                self.add_text('@pxref{%s,,%s,%s}' % (id, name, uri))
        else:
            uri = escape_arg(uri)
            name = escape_arg(name)
            if not name or uri == name:
                self.add_text('@indicateurl{%s}' % uri)
            else:
                self.add_text('@uref{%s,%s}' % (uri, name))
        raise nodes.SkipNode

    def depart_reference(self, node):
        pass

    def visit_title_reference(self, node):
        text = node.astext()
        self.add_text('@cite{%s}' % escape_arg(text))
        raise nodes.SkipNode
    def depart_title_reference(self, node):
        pass

    ## Blocks

    def visit_paragraph(self, node):
        if 'continued' in node or isinstance(node.parent, nodes.compound):
            self.add_text('@noindent\n', fresh=1)
    def depart_paragraph(self, node):
        self.add_text('\n\n')

    def visit_block_quote(self, node):
        self.rstrip()
        self.add_text('\n\n@quotation\n')
    def depart_block_quote(self, node):
        self.rstrip()
        self.add_text('\n@end quotation\n\n')

    def visit_literal_block(self, node):
        self.rstrip()
        self.add_text('\n\n@example\n')
    def depart_literal_block(self, node):
        self.rstrip()
        self.add_text('\n@end example\n\n'
                      '@noindent\n')

    visit_doctest_block = visit_literal_block
    depart_doctest_block = depart_literal_block

    def visit_line_block(self, node):
        self.add_text('@display\n', fresh=1)
    def depart_line_block(self, node):
        self.add_text('@end display\n', fresh=1)

    def visit_line(self, node):
        self.rstrip()
        self.add_text('\n')
        self.escape_newlines += 1
    def depart_line(self, node):
        self.add_text('@w{ }\n')
        self.escape_newlines -= 1

    ## Inline

    def visit_strong(self, node):
        self.add_text('@strong{')
    def depart_strong(self, node):
        self.add_text('}')

    def visit_emphasis(self, node):
        self.add_text('@emph{')
    def depart_emphasis(self, node):
        self.add_text('}')

    def visit_literal(self, node):
        self.add_text('@code{')
    def depart_literal(self, node):
        self.add_text('}')

    def visit_superscript(self, node):
        self.add_text('@w{^')
    def depart_superscript(self, node):
        self.add_text('}')

    def visit_subscript(self, node):
        self.add_text('@w{[')
    def depart_subscript(self, node):
        self.add_text(']}')

    ## Footnotes

    def visit_footnote(self, node):
        self.visit_block_quote(node)
    def depart_footnote(self, node):
        self.depart_block_quote(node)

    def visit_footnote_reference(self, node):
        self.add_text('@w{(')
    def depart_footnote_reference(self, node):
        self.add_text(')}')

    visit_citation = visit_footnote
    depart_citation = depart_footnote

    def visit_citation_reference(self, node):
        self.add_text('@w{[')
    def depart_citation_reference(self, node):
        self.add_text(']}')

    ## Lists

    def visit_bullet_list(self, node):
        bullet = node.get('bullet', '*')
        self.rstrip()
        self.add_text('\n\n@itemize %s\n' % bullet)
    def depart_bullet_list(self, node):
        self.rstrip()
        self.add_text('\n@end itemize\n\n')

    def visit_enumerated_list(self, node):
        # Doesn't support Roman numerals
        enum = node.get('enumtype', 'arabic')
        starters = {'arabic': '',
                    'loweralpha': 'a',
                    'upperalpha': 'A',}
        start = node.get('start', starters.get(enum, ''))
        self.rstrip()
        self.add_text('\n\n@enumerate %s\n' % start)
    def depart_enumerated_list(self, node):
        self.rstrip()
        self.add_text('\n@end enumerate\n\n')

    def visit_list_item(self, node):
        self.rstrip()
        self.add_text('\n@item\n')
    def depart_list_item(self, node):
        pass

    ## Option List

    def visit_option_list(self, node):
        self.add_text('\n@table @option\n')
    def depart_option_list(self, node):
        self.rstrip()
        self.add_text('\n@end table\n\n')

    def visit_option_list_item(self, node):
        pass
    def depart_option_list_item(self, node):
        pass

    def visit_option_group(self, node):
        self.at_item_x = '@item'
    def depart_option_group(self, node):
        pass

    def visit_option(self, node):
        self.add_text(self.at_item_x + ' ', fresh=1)
        self.at_item_x = '@itemx'
    def depart_option(self, node):
        pass

    def visit_option_string(self, node):
        pass
    def depart_option_string(self, node):
        pass

    def visit_option_argument(self, node):
        self.add_text(node.get('delimiter', ' '))
    def depart_option_argument(self, node):
        pass

    def visit_description(self, node):
        self.add_text('', fresh=1)
    def depart_description(self, node):
        pass

    ## Definitions

    def visit_definition_list(self, node):
        self.add_text('\n@table @asis\n')
    def depart_definition_list(self, node):
        self.rstrip()
        self.add_text('\n@end table\n\n')

    def visit_definition_list_item(self, node):
        self.at_item_x = '@item'
    def depart_definition_list_item(self, node):
        pass

    def visit_term(self, node):
        if node.get('ids') and node['ids'][0]:
            self.add_anchor(node['ids'][0], node)
        self.add_text(self.at_item_x + ' ', fresh=1)
        self.at_item_x = '@itemx'
    def depart_term(self, node):
        pass

    def visit_termsep(self, node):
        self.add_text(self.at_item_x + ' ', fresh=1)

    def visit_classifier(self, node):
        self.add_text(' : ')
    def depart_classifier(self, node):
        pass

    def visit_definition(self, node):
        self.add_text('', fresh=1)
    def depart_definition(self, node):
        pass

    ## Tables

    def visit_table(self, node):
        self.entry_sep = '@item'
    def depart_table(self, node):
        self.rstrip()
        self.add_text('\n@end multitable\n\n')

    def visit_tabular_col_spec(self, node):
        pass
    def depart_tabular_col_spec(self, node):
        pass

    def visit_colspec(self, node):
        self.colwidths.append(node['colwidth'])
        if len(self.colwidths) != self.n_cols:
            return
        self.add_text('@multitable ', fresh=1)
        for i, n in enumerate(self.colwidths):
            self.add_text('{%s} ' %('x' * (n+2)))
    def depart_colspec(self, node):
        pass

    def visit_tgroup(self, node):
        self.colwidths = []
        self.n_cols = node['cols']
    def depart_tgroup(self, node):
        pass

    def visit_thead(self, node):
        self.entry_sep = '@headitem'
    def depart_thead(self, node):
        pass

    def visit_tbody(self, node):
        pass
    def depart_tbody(self, node):
        pass

    def visit_row(self, node):
        pass
    def depart_row(self, node):
        self.entry_sep = '@item'

    def visit_entry(self, node):
        self.rstrip()
        self.add_text('\n%s ' % self.entry_sep)
        self.entry_sep = '@tab'
    def depart_entry(self, node):
        for i in xrange(node.get('morecols', 0)):
            self.add_text('@tab\n', fresh=1)
        self.add_text('', fresh=1)

    ## Field Lists

    def visit_field_list(self, node):
        self.add_text('\n@itemize @w\n')
    def depart_field_list(self, node):
        self.rstrip()
        self.add_text('\n@end itemize\n\n')

    def visit_field(self, node):
        if not isinstance(node.parent, nodes.field_list):
            self.visit_field_list(None)
    def depart_field(self, node):
        if not isinstance(node.parent, nodes.field_list):
            self.depart_field_list(None)

    def visit_field_name(self, node):
        self.add_text('@item ', fresh=1)
    def depart_field_name(self, node):
        self.add_text(':')

    def visit_field_body(self, node):
        self.add_text('', fresh=1)
    def depart_field_body(self, node):
        pass

    ## Admonitions

    def visit_admonition(self, node):
        title = escape(node[0].astext())
        self.add_text('\n@cartouche\n'
                       '@quotation %s\n' % title)
    def depart_admonition(self, node):
        self.rstrip()
        self.add_text('\n@end quotation\n'
                       '@end cartouche\n\n')

    def _make_visit_admonition(typ):
        def visit(self, node):
            title = escape(typ)
            self.add_text('\n@cartouche\n'
                          '@quotation %s\n' % title)
        return visit

    visit_attention = _make_visit_admonition('Attention')
    visit_caution   = _make_visit_admonition('Caution')
    visit_danger    = _make_visit_admonition('Danger')
    visit_error     = _make_visit_admonition('Error')
    visit_important = _make_visit_admonition('Important')
    visit_note      = _make_visit_admonition('Note')
    visit_tip       = _make_visit_admonition('Tip')
    visit_hint      = _make_visit_admonition('Hint')
    visit_warning   = _make_visit_admonition('Warning')

    depart_attention = depart_admonition
    depart_caution   = depart_admonition
    depart_danger    = depart_admonition
    depart_error     = depart_admonition
    depart_important = depart_admonition
    depart_note      = depart_admonition
    depart_tip       = depart_admonition
    depart_hint      = depart_admonition
    depart_warning   = depart_admonition

    ## Misc

    def visit_docinfo(self, node):
        # No 'docinfo_xform'
        raise nodes.SkipNode

    def visit_topic(self, node):
        # Ignore TOC's since we have to have a "menu" anyway
        if 'contents' in node.get('classes', []):
            raise nodes.SkipNode
        title = node[0]
        self.visit_rubric(title)
        self.add_text('%s\n' % escape(title.astext()))
        self.visit_block_quote(node)
    def depart_topic(self, node):
        self.depart_block_quote(node)

    def visit_generated(self, node):
        raise nodes.SkipNode
    def depart_generated(self, node):
        pass

    def visit_transition(self, node):
        self.add_text('\n\n@noindent\n'
                      '@exdent @w{%s}\n\n'
                      '@noindent\n' % ('_' * 70))
    def depart_transition(self, node):
        pass

    def visit_attribution(self, node):
        self.add_text('@flushright\n', fresh=1)
    def depart_attribution(self, node):
        self.add_text('@end flushright\n', fresh=1)

    def visit_raw(self, node):
        format = node.get('format', '').split()
        if 'texinfo' in format or 'texi' in format:
            self.add_text(node.astext())
        raise nodes.SkipNode
    def depart_raw(self, node):
        pass

    def visit_figure(self, node):
        self.add_text('\n@float Figure\n')
    def depart_figure(self, node):
        self.rstrip()
        self.add_text('\n@end float\n\n')

    def visit_caption(self, node):
        if not isinstance(node.parent, nodes.figure):
            self.document.reporter.warning('Caption not inside a figure.',
                                           base_node=node)
            return
        self.add_text('@caption{', fresh=1)
    def depart_caption(self, node):
        if isinstance(node.parent, nodes.figure):
            self.rstrip()
            self.add_text('}\n')

    def visit_image(self, node):
        if node['uri'] in self.builder.images:
            uri = self.builder.images[node['uri']]
        else:
            # missing image!
            if self.ignore_missing_images:
                return
            uri = node['uri']
        if uri.find('://') != -1:
            # ignore remote images
            return
        name, ext = path.splitext(uri)
        attrs = node.attributes
        # ignored in non-tex output
        width = self.tex_image_length(attrs.get('width', ''))
        height = self.tex_image_length(attrs.get('height', ''))
        alt = escape_arg(attrs.get('alt', ''))
        self.add_text('\n\n@image{%s,%s,%s,%s,%s}\n\n' %
                      (name, width, height, alt, ext[1:]))
    def depart_image(self, node):
        pass

    def visit_compound(self, node):
        pass
    def depart_compound(self, node):
        pass

    def visit_sidebar(self, node):
        pass
    def depart_sidebar(self, node):
        pass

    def visit_label(self, node):
        self.add_text('@w{(')
    def depart_label(self, node):
        self.add_text(')} ')

    def visit_legend(self, node):
        pass
    def depart_legend(self, node):
        pass

    def visit_substitution_reference(self, node):
        pass
    def depart_substitution_reference(self, node):
        pass

    def visit_substitution_definition(self, node):
        raise nodes.SkipNode
    def depart_substitution_definition(self, node):
        pass

    def visit_system_message(self, node):
        self.add_text('\n@format\n'
                       '---------- SYSTEM MESSAGE -----------\n')
    def depart_system_message(self, node):
        self.rstrip()
        self.add_text('\n------------------------------------\n'
                      '@end format\n')

    def visit_comment(self, node):
        for line in node.astext().splitlines():
            self.add_text('@c %s\n' % line, fresh=1)
        raise nodes.SkipNode

    def visit_problematic(self, node):
        self.add_text('>')
    def depart_problematic(self, node):
        self.add_text('<')

    def unimplemented_visit(self, node):
        self.document.reporter.error("Unimplemented node type: `%s'"
                                     % node.__class__.__name__, base_node=node)

    def unknown_visit(self, node):
        self.document.reporter.error("Unknown node type: `%s'"
                                     % node.__class__.__name__, base_node=node)
    def unknown_departure(self, node):
        pass

    ### Sphinx specific

    def visit_productionlist(self, node):
        self.visit_literal_block(None)
        names = []
        for production in node:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        for production in node:
            if production['tokenname']:
                s = production['tokenname'].ljust(maxlen) + ' ::='
                lastname = production['tokenname']
            else:
                s = '%s    ' % (' '*len(lastname))
            self.add_text(escape(s))
            self.add_text(escape(production.astext() + '\n'))
        self.depart_literal_block(None)
        raise nodes.SkipNode
    def depart_productionlist(self, node):
        pass

    def visit_literal_emphasis(self, node):
        self.add_text('@code{')
    def depart_literal_emphasis(self, node):
        self.add_text('}')

    def visit_module(self, node):
        modname = escape_id(node['modname'])
        self.add_anchor(modname, node)

    def visit_index(self, node):
        # Throws off table alignment
        if isinstance(node.parent, nodes.term):
            return
        for entry in node['entries']:
            typ, text, tid, text2 = entry
            text = text.replace('()', ' ').replace('(', '[').replace(')', ']')
            text = escape_id(text)
            self.add_text('@geindex %s\n' % text, fresh=1)

    def visit_autosummary_table(self, node):
        pass
    def depart_autosummary_table(self, node):
        pass

    def visit_todo_node(self, node):
        self.visit_transition(node)
        self.visit_admonition(node)
    def depart_todo_node(self, node):
        self.depart_admonition(node)
        self.visit_transition(node)

    def visit_refcount(self, node):
        self.add_text('\n')
    def depart_refcount(self, node):
        self.add_text('\n\n')

    def visit_versionmodified(self, node):
        intro = versionlabels[node['type']] % node['version']
        if node.children:
            intro += ': '
        else:
            intro += '.'
        self.add_text('%s' % escape(intro), fresh=1)
    def depart_versionmodified(self, node):
        self.rstrip()
        self.add_text('\n\n', fresh=1)

    def visit_start_of_file(self, node):
        self.curfilestack.append(node.get('docname', ''))
        if node.get('docname'):
            self.next_section_targets.append(node['docname'])
    def depart_start_of_file(self, node):
        self.curfilestack.pop()

    def visit_centered(self, node):
        txt = escape_arg(node.astext())
        self.add_text('@center %s\n' % txt, fresh=1)
        raise nodes.SkipNode
    def depart_centered(self, node):
        pass

    def visit_seealso(self, node):
        pass
    def depart_seealso(self, node):
        pass

    def visit_meta(self, node):
        raise nodes.SkipNode
    def depart_meta(self, node):
        pass

    def visit_glossary(self, node):
        pass
    def depart_glossary(self, node):
        pass

    def visit_acks(self, node):
        pass
    def depart_acks(self, node):
        pass

    def visit_highlightlang(self, node):
        pass
    def depart_highlightlang(self, node):
        pass

    ## Desc

    desc_map = {
        'function' : 'Function',
        'class': 'Class',
        'method': 'Method',
        'classmethod': 'Class Method',
        'staticmethod': 'Static Method',
        'exception': 'Exception',
        'data': 'Data',
        'attribute': 'Attribute',
        'opcode': 'Opcode',
        'cfunction': 'C Function',
        'cmember': 'C Member',
        'cmacro': 'C Macro',
        'ctype': 'C Type',
        'cvar': 'C Variable',
        'cmdoption': 'Option',
        'describe': 'Description',
        }

    def visit_desc(self, node):
        self.at_deffnx = '@deffn'
    def depart_desc(self, node):
        self.rstrip()
        self.add_text('@end deffn\n\n', fresh=1)
    def visit_desc_signature(self, node):
        self.desctype = node.parent['desctype'].strip()
        if self.desctype != 'describe' and node['ids']:
            self.add_anchor(node['ids'][0], node)
        typ = self.desc_map.get(self.desctype, self.desctype)
        self.add_text('%s {%s} ' % (self.at_deffnx, escape_arg(typ)), fresh=1)
        self.at_deffnx = '@deffnx'
    def depart_desc_signature(self, node):
        self.add_text("", fresh=1)

    def visit_desc_name(self, node):
        pass
    def depart_desc_name(self, node):
        pass

    def visit_desc_addname(self, node):
        pass
    def depart_desc_addname(self, node):
        pass

    def visit_desc_type(self, node):
        pass
    def depart_desc_type(self, node):
        pass

    def visit_desc_returns(self, node):
        self.add_text(' -> ')
    def depart_desc_returns(self, node):
        pass

    def visit_desc_parameterlist(self, node):
        self.add_text(' (')
        self.first_param = 1
    def depart_desc_parameterlist(self, node):
        self.add_text(')')

    def visit_desc_parameter(self, node):
        if not self.first_param:
            self.add_text(', ')
        else:
            self.first_param = 0
        self.add_text(escape(node.astext()))
        raise nodes.SkipNode
    def depart_desc_parameter(self, node):
        pass

    def visit_desc_optional(self, node):
        self.add_text('[')
    def depart_desc_optional(self, node):
        self.add_text(']')

    def visit_desc_annotation(self, node):
        raise nodes.SkipNode
    def depart_desc_annotation(self, node):
        pass

    def visit_desc_content(self, node):
        self.add_text("", fresh=1)
    def depart_desc_content(self, node):
        pass

    def visit_inline(self, node):
        # stub
        pass
    def depart_inline(self, node):
        pass

    def visit_abbreviation(self, node):
        self.add_text('@abbr{')
        if node.hasattr('explanation'):
            self.context.append(', %s}' % escape_arg(node['explanation']))
        else:
            self.context.append('}')
    def depart_abbreviation(self, node):
        self.body.append(self.context.pop())

    def visit_download_reference(self, node):
        pass
    def depart_download_reference(self, node):
        pass

    def visit_hlist(self, node):
        # stub
        self.visit_bullet_list(node)
    def depart_hlist(self, node):
        self.depart_bullet_list(node)

    def visit_hlistcol(self, node):
        pass
    def depart_hlistcol(self, node):
        pass
