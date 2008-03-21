# -*- coding: utf-8 -*-
"""
    sphinx.ext.doctest
    ~~~~~~~~~~~~~~~~~~

    Mimic doctest by automatically executing code snippets and checking
    their results.

    :copyright: 2008 by Georg Brandl.
    :license: BSD.
"""

import sys
import time
import StringIO
from os import path
# circumvent relative import
doctest = __import__('doctest')

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx.builder import Builder


# set up the necessary directives

def test_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    # use ordinary docutils nodes for test code: they get special attributes
    # so that our builder recognizes them, and the other builders are happy.
    code = '\n'.join(content)
    nodetype = nodes.literal_block
    if name == 'testsetup' or \
       (name == 'testoutput' and 'hide' in options):
        nodetype = nodes.comment
    node = nodetype(code, code)
    node.line = lineno
    if arguments:
        groups = [x.strip() for x in arguments[0].split(',')]
    else:
        groups = ['default']
    node['testnodetype'] = name
    node['groups'] = groups
    if name == 'testoutput':
        # don't try to highlight output
        node['language'] = 'none'
    node['options'] = {}
    if name == 'testoutput' and 'options' in options:
        # parse doctest-like output comparison flags
        option_strings = options['options'].replace(',', ' ').split()
        for option in option_strings:
            if (option[0] not in '+-' or option[1:] not in
                doctest.OPTIONFLAGS_BY_NAME):
                # XXX warn?
                continue
            flag = doctest.OPTIONFLAGS_BY_NAME[option[1:]]
            node['options'][flag] = (option[0] == '+')
    return [node]

# need to have individual functions for each directive due to different
# options they accept

def testsetup_directive(*args):
    return test_directive(*args)

def doctest_directive(*args):
    return test_directive(*args)

def testcode_directive(*args):
    return test_directive(*args)

def testoutput_directive(*args):
    return test_directive(*args)


parser = doctest.DocTestParser()

# helper classes

class TestGroup(object):
    def __init__(self, name):
        self.name = name
        self.setup = []
        self.tests = []

    def add_code(self, code):
        if code.type == 'testsetup':
            self.setup.append(code)
        elif code.type == 'doctest':
            self.tests.append([code])
        elif code.type == 'testcode':
            self.tests.append([code, None])
        elif code.type == 'testoutput':
            if self.tests and len(self.tests[-1]) == 2:
                self.tests[-1][1] = code
        else:
            raise RuntimeError('invalid TestCode type')

    def __repr__(self):
        return 'TestGroup(name=%r, setup=%r, code=%r)' % (
            self.name, self.setup, self.code)


class TestCode(object):
    def __init__(self, code, type, lineno, options=None):
        self.code = code
        self.type = type
        self.lineno = lineno
        self.options = options or {}

    def __repr__(self):
        return 'TestCode(%r, %r, %r, options=%r)' % (
            self.code, self.type, self.lineno, self.options)


class SphinxDocTestRunner(doctest.DocTestRunner):
    def summarize(self, out, verbose=None):
        io = StringIO.StringIO()
        old_stdout = sys.stdout
        sys.stdout = io
        try:
            res = doctest.DocTestRunner.summarize(self, verbose)
        finally:
            sys.stdout = old_stdout
        out(io.getvalue())
        return res

# the new builder -- use sphinx-build.py -b doctest to run

class DocTestBuilder(Builder):
    """
    Runs test snippets in the documentation.
    """
    name = 'doctest'

    def init(self):
        # default options
        self.opt = doctest.DONT_ACCEPT_TRUE_FOR_1 | doctest.ELLIPSIS | \
                   doctest.IGNORE_EXCEPTION_DETAIL

        self.total_failures = 0
        self.total_tries = 0
        self.setup_failures = 0
        self.setup_tries = 0

        date = time.strftime('%Y-%m-%d %H:%M:%S')

        self.outfile = file(path.join(self.outdir, 'output.txt'), 'w')
        self.outfile.write('''\
Results of doctest builder run on %s
==================================%s
''' % (date, '='*len(date)))

    def _out(self, text):
        self.info(text, nonl=True)
        self.outfile.write(text)

    def get_target_uri(self, docname, typ=None):
        return ''

    def get_outdated_docs(self):
        return self.env.all_docs

    def prepare_writing(self, docnames):
        return

    def finish(self):
        # write executive summary
        def s(v):
            return v != 1 and 's' or ''
        self._out('''
Doctest summary
===============
%5d test%s
%5d failure%s in tests
%5d failure%s in setup code
''' % (self.total_tries, s(self.total_tries),
       self.total_failures, s(self.total_failures),
       self.setup_failures, s(self.setup_failures)))
        self.outfile.close()

        sys.path[0:0] = self.config.doctest_path

    def write_doc(self, docname, doctree):
        groups = {}
        add_to_all_groups = []
        self.setup_runner = SphinxDocTestRunner(verbose=False,
                                                optionflags=self.opt)
        self.test_runner = SphinxDocTestRunner(verbose=False,
                                               optionflags=self.opt)
        self.info()
        if self.config.doctest_test_doctest_blocks:
            def condition(node):
                return (isinstance(node, (nodes.literal_block, nodes.comment))
                        and node.has_key('testnodetype')) or \
                       isinstance(node, nodes.doctest_block)
        else:
            def condition(node):
                return isinstance(node, (nodes.literal_block, nodes.comment)) \
                        and node.has_key('testnodetype')
        for node in doctree.traverse(condition):
            code = TestCode(node.astext(),
                            type=node.get('testnodetype', 'doctest'),
                            lineno=node.line, options=node.get('options'))
            node_groups = node.get('groups', ['doctest_block'])
            if '*' in node_groups:
                add_to_all_groups.append(code)
                continue
            for groupname in node_groups:
                if groupname not in groups:
                    groups[groupname] = TestGroup(groupname)
                groups[groupname].add_code(code)
        for code in add_to_all_groups:
            for group in groups.itervalues():
                group.add_code(code)
        if not groups:
            return

        self.outfile.write('\nDocument: %s\n----------%s\n' %
                           (docname, '-'*len(docname)))
        for group in groups.itervalues():
            self.test_group(group, self.env.doc2path(docname, base=None))
        # Separately count results from setup code
        res_f, res_t = self.setup_runner.summarize(self._out, verbose=False)
        self.setup_failures += res_f
        self.setup_tries += res_t
        if self.test_runner.tries:
            res_f, res_t = self.test_runner.summarize(self._out, verbose=True)
            self.total_failures += res_f
            self.total_tries += res_t

    def test_group(self, group, filename):
        ns = {}
        examples = []
        for setup in group.setup:
            examples.append(doctest.Example(setup.code, '', lineno=setup.lineno))
        if examples:
            # simulate a doctest with the setup code
            setup_doctest = doctest.DocTest(examples, {},
                                            '%s (setup code)' % group.name,
                                            filename, 0, None)
            setup_doctest.globs = ns
            old_f = self.setup_runner.failures
            self.setup_runner.run(setup_doctest, out=self._out,
                                  clear_globs=False)
            if self.setup_runner.failures > old_f:
                # don't run the group
                return
        for code in group.tests:
            if len(code) == 1:
                test = parser.get_doctest(code[0].code, {},
                                          group.name, filename, code[0].lineno)
                if not test.examples:
                    self._out('WARNING: no examples in doctest block at '
                              + filename + ', line %s' % code[0].lineno)
                    continue
            else:
                output = code[1] and code[1].code or ''
                options = code[1] and code[1].options or None
                example = doctest.Example(code[0].code, output,
                                          lineno=code[0].lineno,
                                          options=options)
                test = doctest.DocTest([example], {}, group.name,
                                       filename, code[0].lineno, None)
            # DocTest.__init__ copies the globs namespace, which we don't want
            test.globs = ns
            # also don't clear the globs namespace after running the doctest
            self.test_runner.run(test, out=self._out, clear_globs=False)


def setup(app):
    app.add_directive('testsetup', testsetup_directive, 1, (0, 1, 1))
    app.add_directive('doctest', doctest_directive, 1, (0, 1, 1))
    app.add_directive('testcode', testcode_directive, 1, (0, 1, 1))
    app.add_directive('testoutput', testoutput_directive, 1, (0, 1, 1),
                      hide=directives.flag, options=directives.unchanged)
    app.add_builder(DocTestBuilder)
    # this config value adds to sys.path
    app.add_config_value('doctest_path', [], False)
    app.add_config_value('doctest_test_doctest_blocks', True, False)
