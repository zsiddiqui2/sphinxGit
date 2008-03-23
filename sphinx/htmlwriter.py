# -*- coding: utf-8 -*-
"""
    sphinx.htmlwriter
    ~~~~~~~~~~~~~~~~~

    docutils writers handling Sphinx' custom nodes.

    :copyright: 2007-2008 by Georg Brandl.
    :license: BSD.
"""

import sys

from docutils import nodes
from docutils.writers.html4css1 import Writer, HTMLTranslator as BaseTranslator

from sphinx.highlighting import PygmentsBridge
from sphinx.util.smartypants import sphinx_smarty_pants


class HTMLWriter(Writer):
    def __init__(self, builder):
        Writer.__init__(self)
        self.builder = builder

    def translate(self):
        # sadly, this is mostly copied from parent class
        self.visitor = visitor = self.builder.translator_class(self.builder,
                                                               self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()
        for attr in ('head_prefix', 'stylesheet', 'head', 'body_prefix',
                     'body_pre_docinfo', 'docinfo', 'body', 'fragment',
                     'body_suffix', 'meta', 'title', 'subtitle', 'header',
                     'footer', 'html_prolog', 'html_head', 'html_title',
                     'html_subtitle', 'html_body', ):
            setattr(self, attr, getattr(visitor, attr, None))


version_text = {
    'deprecated': 'Deprecated in version %s',
    'versionchanged': 'Changed in version %s',
    'versionadded': 'New in version %s',
}

class HTMLTranslator(BaseTranslator):
    """
    Our custom HTML translator.
    """

    def __init__(self, builder, *args, **kwds):
        BaseTranslator.__init__(self, *args, **kwds)
        self.highlighter = PygmentsBridge('html', builder.config.pygments_style)
        self.no_smarty = 0
        self.builder = builder
        self.highlightlang = 'python'
        self.highlightlinenothreshold = sys.maxint
        self.language.labels['warning'] = 'Caveat'

    def visit_desc(self, node):
        self.body.append(self.starttag(node, 'dl', CLASS=node['desctype']))
    def depart_desc(self, node):
        self.body.append('</dl>\n\n')

    def visit_desc_signature(self, node):
        # the id is set automatically
        self.body.append(self.starttag(node, 'dt'))
        # anchor for per-desc interactive data
        if node.parent['desctype'] != 'describe' and node['ids'] and node['first']:
            self.body.append('<!--#%s#-->' % node['ids'][0])
        if node.parent['desctype'] in ('class', 'exception'):
            self.body.append('%s ' % node.parent['desctype'])
    def depart_desc_signature(self, node):
        if node['ids'] and self.builder.name != 'htmlhelp':
            self.body.append(u'<a class="headerlink" href="#%s" ' % node['ids'][0] +
                             u'title="Permalink to this definition">\u00B6</a>')
        self.body.append('</dt>\n')

    def visit_desc_classname(self, node):
        self.body.append(self.starttag(node, 'tt', '', CLASS='descclassname'))
    def depart_desc_classname(self, node):
        self.body.append('</tt>')

    def visit_desc_type(self, node):
        # return type of C functions -- nothing to do here
        pass
    def depart_desc_type(self, node):
        pass

    def visit_desc_name(self, node):
        self.body.append(self.starttag(node, 'tt', '', CLASS='descname'))
    def depart_desc_name(self, node):
        self.body.append('</tt>')

    def visit_desc_parameterlist(self, node):
        self.body.append('<big>(</big>')
        self.first_param = 1
    def depart_desc_parameterlist(self, node):
        self.body.append('<big>)</big>')

    def visit_desc_parameter(self, node):
        if not self.first_param:
            self.body.append(', ')
        else:
            self.first_param = 0
        if not node.hasattr('noemph'):
            self.body.append('<em>')
    def depart_desc_parameter(self, node):
        if not node.hasattr('noemph'):
            self.body.append('</em>')

    def visit_desc_optional(self, node):
        self.body.append('<span class="optional">[</span>')
    def depart_desc_optional(self, node):
        self.body.append('<span class="optional">]</span>')

    def visit_desc_content(self, node):
        self.body.append(self.starttag(node, 'dd', ''))
    def depart_desc_content(self, node):
        self.body.append('</dd>')

    def visit_refcount(self, node):
        self.body.append(self.starttag(node, 'em', '', CLASS='refcount'))
    def depart_refcount(self, node):
        self.body.append('</em>')

    def visit_versionmodified(self, node):
        self.body.append(self.starttag(node, 'p'))
        text = version_text[node['type']] % node['version']
        if len(node):
            text += ': '
        else:
            text += '.'
        self.body.append('<span class="versionmodified">%s</span>' % text)
    def depart_versionmodified(self, node):
        self.body.append('</p>\n')

    # overwritten
    def visit_reference(self, node):
        BaseTranslator.visit_reference(self, node)
        if node.hasattr('reftitle'):
            # ugly hack to add a title attribute
            starttag = self.body[-1]
            if not starttag.startswith('<a '):
                return
            self.body[-1] = '<a title="%s"' % self.attval(node['reftitle']) + \
                            starttag[2:]

    # overwritten -- we don't want source comments to show up in the HTML
    def visit_comment(self, node):
        raise nodes.SkipNode

    # overwritten
    def visit_admonition(self, node, name=''):
        self.body.append(self.starttag(
            node, 'div', CLASS=('admonition ' + name)))
        if name and name != 'seealso':
            node.insert(0, nodes.title(name, self.language.labels[name]))
        self.set_first_last(node)

    def visit_seealso(self, node):
        self.visit_admonition(node, 'seealso')
    def depart_seealso(self, node):
        self.depart_admonition(node)

    # overwritten (args/kwds due to docutils 0.4/0.5 incompatibility)
    def visit_title(self, node, *args, **kwds):
        # if we have a section we do our own processing in order
        # to have ids in the hN-tags and not in additional a-tags
        if isinstance(node.parent, nodes.section):
            h_level = self.section_level + self.initial_header_level - 1
            if node.parent.get('ids'):
                attrs = {'ids': node.parent['ids']}
            else:
                attrs = {}
            self.body.append(self.starttag(node, 'h%d' % h_level, '', **attrs))
            self.context.append('</h%d>\n' % h_level)
        else:
            BaseTranslator.visit_title(self, node, *args, **kwds)

    # overwritten
    def visit_literal_block(self, node):
        lang = self.highlightlang
        linenos = node.rawsource.count('\n') >= self.highlightlinenothreshold - 1
        if node.has_key('language'):
            # code-block directives
            lang = node['language']
        if node.has_key('linenos'):
            linenos = node['linenos']
        self.body.append(self.highlighter.highlight_block(node.rawsource,
                                                          lang, linenos))
        raise nodes.SkipNode

    def visit_doctest_block(self, node):
        self.visit_literal_block(node)

    # overwritten
    def visit_literal(self, node):
        if len(node.children) == 1 and \
               node.children[0] in ('None', 'True', 'False'):
            node['classes'].append('xref')
        BaseTranslator.visit_literal(self, node)

    def visit_productionlist(self, node):
        self.body.append(self.starttag(node, 'pre'))
        names = []
        for production in node:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        for production in node:
            if production['tokenname']:
                self.body.append(self.starttag(production, 'strong', ''))
                self.body.append(production['tokenname'].ljust(maxlen) +
                                 '</strong> ::= ')
                lastname = production['tokenname']
            else:
                self.body.append('%s     ' % (' '*len(lastname)))
            production.walkabout(self)
            self.body.append('\n')
        self.body.append('</pre>\n')
        raise nodes.SkipNode
    def depart_productionlist(self, node):
        pass

    def visit_production(self, node):
        pass
    def depart_production(self, node):
        pass

    def visit_centered(self, node):
        self.body.append(self.starttag(node, 'p', CLASS="centered") + '<strong>')
    def depart_centered(self, node):
        self.body.append('</strong></p>')

    def visit_compact_paragraph(self, node):
        pass
    def depart_compact_paragraph(self, node):
        pass

    def visit_highlightlang(self, node):
        self.highlightlang = node['lang']
        self.highlightlinenothreshold = node['linenothreshold']
    def depart_highlightlang(self, node):
        pass

    def visit_toctree(self, node):
        # this only happens when formatting a toc from env.tocs -- in this
        # case we don't want to include the subtree
        raise nodes.SkipNode

    def visit_index(self, node):
        raise nodes.SkipNode

    def visit_glossary(self, node):
        pass
    def depart_glossary(self, node):
        pass

    def visit_acks(self, node):
        pass
    def depart_acks(self, node):
        pass

    def visit_module(self, node):
        pass
    def depart_module(self, node):
        pass

    # docutils 0.5 compatibility
    def visit_note(self, node):
        self.visit_admonition(node, 'note')
    def depart_note(self, node):
        self.depart_admonition(node)

    # docutils 0.5 compatibility
    def visit_warning(self, node):
        self.visit_admonition(node, 'warning')
    def depart_warning(self, node):
        self.depart_admonition(node)

    # these are only handled specially in the SmartyPantsHTMLTranslator
    def visit_literal_emphasis(self, node):
        return self.visit_emphasis(node)
    def depart_literal_emphasis(self, node):
        return self.depart_emphasis(node)

    def depart_title(self, node):
        close_tag = self.context[-1]
        if self.builder.name != 'htmlhelp' and \
               (close_tag.startswith('</h') or
                close_tag.startswith('</a></h')) and \
               node.parent.hasattr('ids') and node.parent['ids']:
            aname = node.parent['ids'][0]
            # add permalink anchor
            self.body.append(u'<a class="headerlink" href="#%s" ' % aname +
                             u'title="Permalink to this headline">\u00B6</a>')
        BaseTranslator.depart_title(self, node)


class SmartyPantsHTMLTranslator(HTMLTranslator):
    """
    Handle ordinary text via smartypants, converting quotes and dashes
    to the correct entities.
    """

    def __init__(self, *args, **kwds):
        self.no_smarty = 0
        HTMLTranslator.__init__(self, *args, **kwds)

    def visit_literal(self, node):
        self.no_smarty += 1
        try:
            # this raises SkipNode
            HTMLTranslator.visit_literal(self, node)
        finally:
            self.no_smarty -= 1

    def visit_literal_emphasis(self, node):
        self.no_smarty += 1
        self.visit_emphasis(node)

    def depart_literal_emphasis(self, node):
        self.depart_emphasis(node)
        self.no_smarty -= 1

    def visit_desc_signature(self, node):
        self.no_smarty += 1
        HTMLTranslator.visit_desc_signature(self, node)

    def depart_desc_signature(self, node):
        self.no_smarty -= 1
        HTMLTranslator.depart_desc_signature(self, node)

    def visit_productionlist(self, node):
        self.no_smarty += 1
        try:
            HTMLTranslator.visit_productionlist(self, node)
        finally:
            self.no_smarty -= 1

    def encode(self, text):
        text = HTMLTranslator.encode(self, text)
        if self.no_smarty <= 0:
            text = sphinx_smarty_pants(text)
        return text
