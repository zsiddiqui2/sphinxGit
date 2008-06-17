# -*- coding: utf-8 -*-
"""
    sphinx.roles
    ~~~~~~~~~~~~

    Handlers for additional ReST roles.

    :copyright: 2007-2008 by Georg Brandl.
    :license: BSD.
"""

import re

from docutils import nodes, utils
from docutils.parsers.rst import roles

from sphinx import addnodes

ws_re = re.compile(r'\s+')
caption_ref_re = re.compile(r'^([^<]+?)\s*<(.+)>$')

generic_docroles = {
    'command' : nodes.strong,
    'dfn' : nodes.emphasis,
    'guilabel' : nodes.strong,
    'kbd' : nodes.literal,
    'mailheader' : addnodes.literal_emphasis,
    'makevar' : nodes.Text,
    'manpage' : addnodes.literal_emphasis,
    'mimetype' : addnodes.literal_emphasis,
    'newsgroup' : addnodes.literal_emphasis,
    'program' : nodes.strong,
    'regexp' : nodes.literal,
}

for rolename, nodeclass in generic_docroles.iteritems():
    roles.register_generic_role(rolename, nodeclass)


def indexmarkup_role(typ, rawtext, etext, lineno, inliner, options={}, content=[]):
    env = inliner.document.settings.env
    if not typ:
        typ = env.config.default_role
    text = utils.unescape(etext)
    targetid = 'index-%s' % env.index_num
    env.index_num += 1
    indexnode = addnodes.index()
    targetnode = nodes.target('', '', ids=[targetid])
    inliner.document.note_explicit_target(targetnode)
    if typ == 'envvar':
        env.note_index_entry('single', text, targetid, text)
        env.note_index_entry('single', 'environment variable; %s' % text,
                             targetid, text)
        indexnode['entries'] = [('single', text, targetid, text),
                                ('single', 'environment variable; %s' % text,
                                 targetid, text)]
        xref_nodes = xfileref_role(typ, rawtext, etext, lineno, inliner,
                                   options, content)[0]
        return [indexnode, targetnode] + xref_nodes, []
    elif typ == 'pep':
        env.note_index_entry('single', 'Python Enhancement Proposals!PEP %s' % text,
                             targetid, 'PEP %s' % text)
        indexnode['entries'] = [('single', 'Python Enhancement Proposals!PEP %s' % text,
                                 targetid, 'PEP %s' % text)]
        try:
            pepnum = int(text)
        except ValueError:
            msg = inliner.reporter.error('invalid PEP number %s' % text, line=lineno)
            prb = inliner.problematic(rawtext, rawtext, msg)
            return [prb], [msg]
        ref = inliner.document.settings.pep_base_url + 'pep-%04d' % pepnum
        sn = nodes.strong('PEP '+text, 'PEP '+text)
        rn = nodes.reference('', '', refuri=ref)
        rn += sn
        return [indexnode, targetnode, rn], []
    elif typ == 'rfc':
        env.note_index_entry('single', 'RFC; RFC %s' % text,
                             targetid, 'RFC %s' % text)
        indexnode['entries'] = [('single', 'RFC; RFC %s' % text,
                                 targetid, 'RFC %s' % text)]
        try:
            rfcnum = int(text)
        except ValueError:
            msg = inliner.reporter.error('invalid RFC number %s' % text, line=lineno)
            prb = inliner.problematic(rawtext, rawtext, msg)
            return [prb], [msg]
        ref = inliner.document.settings.rfc_base_url + inliner.rfc_url % rfcnum
        sn = nodes.strong('RFC '+text, 'RFC '+text)
        rn = nodes.reference('', '', refuri=ref)
        rn += sn
        return [indexnode, targetnode, rn], []

roles.register_canonical_role('envvar', indexmarkup_role)
roles.register_local_role('pep', indexmarkup_role)
roles.register_local_role('rfc', indexmarkup_role)


# default is `literal`
innernodetypes = {
    'ref': nodes.emphasis,
    'term': nodes.emphasis,
    'token': nodes.strong,
    'envvar': nodes.strong,
    'option': addnodes.literal_emphasis,
}

def _fix_parens(typ, text, env):
    if typ in ('func', 'meth', 'cfunc'):
        if text.endswith('()'):
            # remove parentheses
            text = text[:-2]
        if env.config.add_function_parentheses:
            # add them back to all occurrences if configured
            text += '()'
    return text

def xfileref_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    env = inliner.document.settings.env
    if not typ:
        typ = env.config.default_role
    text = utils.unescape(text)
    # if the first character is a bang, don't cross-reference at all
    if text[0:1] == '!':
        text = _fix_parens(typ, text[1:], env)
        return [innernodetypes.get(typ, nodes.literal)(
            rawtext, text, classes=['xref'])], []
    # we want a cross-reference, create the reference node
    pnode = addnodes.pending_xref(rawtext, reftype=typ, refcaption=False,
                                  modname=env.currmodule, classname=env.currclass)
    # we may need the line number for warnings
    pnode.line = lineno
    # the link title may differ from the target, but by default they are the same
    title = target = text
    titleistarget = True
    # look if explicit title and target are given with `foo <bar>` syntax
    brace = text.find('<')
    if brace != -1:
        titleistarget = False
        pnode['refcaption'] = True
        m = caption_ref_re.match(text)
        if m:
            target = m.group(2)
            title = m.group(1)
        else:
            # fallback: everything after '<' is the target
            target = text[brace+1:]
            title = text[:brace]
    # special target  for Python object cross-references
    if typ in ('data', 'exc', 'func', 'class', 'const', 'attr', 'meth', 'mod', 'obj'):
        # fix-up parentheses in link title
        if titleistarget:
            title = title.lstrip('.')   # only has a meaning for the target
            target = target.lstrip('~') # only has a meaning for the title
            title = _fix_parens(typ, title, env)
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot+1:]
        # remove parentheses from the target too
        if target.endswith('()'):
            target = target[:-2]
        # if the first character is a dot, search more specific namespaces first
        # else search builtins first
        if target[0:1] == '.':
            target = target[1:]
            pnode['refspecific'] = True
    # some other special cases for the target
    elif typ == 'option' and target[0] in '-/':
        # strip option marker from target
        target = target[1:]
    elif typ == 'term':
        # normalize whitespace in definition terms (if the term reference is
        # broken over a line, a newline will be in target)
        target = ws_re.sub(' ', target).lower()
    else:
        # remove all whitespace to avoid referencing problems
        target = ws_re.sub('', target)
    pnode['reftarget'] = target
    pnode += innernodetypes.get(typ, nodes.literal)(rawtext, title, classes=['xref'])
    return [pnode], []


def menusel_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    return [nodes.emphasis(
        rawtext, utils.unescape(text).replace('-->', u'\N{TRIANGULAR BULLET}'))], []


_litvar_re = re.compile('{([^}]+)}')

def emph_literal_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    retnodes = []
    pos = 0
    for m in _litvar_re.finditer(text):
        if m.start() > pos:
            txt = text[pos:m.start()]
            retnodes.append(nodes.literal(txt, txt))
        retnodes.append(nodes.emphasis('', '', nodes.literal(m.group(1), m.group(1))))
        pos = m.end()
    if pos < len(text):
        retnodes.append(nodes.literal(text[pos:], text[pos:]))
    return retnodes, []


specific_docroles = {
    'data': xfileref_role,
    'exc': xfileref_role,
    'func': xfileref_role,
    'class': xfileref_role,
    'const': xfileref_role,
    'attr': xfileref_role,
    'meth': xfileref_role,
    'obj': xfileref_role,
    'cfunc' : xfileref_role,
    'cdata' : xfileref_role,
    'ctype' : xfileref_role,
    'cmacro' : xfileref_role,

    'mod' : xfileref_role,

    'keyword': xfileref_role,
    'ref': xfileref_role,
    'token' : xfileref_role,
    'term': xfileref_role,
    'option': xfileref_role,

    'menuselection' : menusel_role,
    'file' : emph_literal_role,
    'samp' : emph_literal_role,
}

for rolename, func in specific_docroles.iteritems():
    roles.register_canonical_role(rolename, func)
