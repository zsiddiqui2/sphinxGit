# -*- coding: utf-8 -*-
"""
    test_env
    ~~~~~~~~

    Test the BuildEnvironment class.

    :copyright: 2008 by Georg Brandl.
    :license: BSD.
"""

from util import *

from sphinx.environment import BuildEnvironment
from sphinx.builder import StandaloneHTMLBuilder, LaTeXBuilder

app = env = None
warnings = []

def setup_module():
    global app, env
    app = TestApp(srcdir='(temp)')
    env = BuildEnvironment(app.srcdir, app.doctreedir, app.config)
    env.set_warnfunc(warnings.append)

def teardown_module():
    app.cleanup()

def warning_emitted(file, text):
    for warning in warnings:
        if file+':' in warning and text in warning:
            return True
    return False

# Tests are run in the order they appear in the file, therefore we can
# afford to not run update() in the setup but in its own test

def test_first_update():
    it = env.update(app.config, app.srcdir, app.doctreedir, app)
    msg = it.next()
    assert msg.endswith('%d added, 0 changed, 0 removed' % len(env.found_docs))
    docnames = set()
    for docname in it:  # the generator does all the work
        docnames.add(docname)
    assert docnames == env.found_docs == set(env.all_docs)

def test_images():
    assert warning_emitted('images.txt', 'Image file not readable: foo.png')
    assert warning_emitted('images.txt', 'Nonlocal image URI found: '
                           'http://www.python.org/logo.png')

    tree = env.get_doctree('images')
    app._warning.reset()
    htmlbuilder = StandaloneHTMLBuilder(app, env)
    htmlbuilder.post_process_images(tree)
    assert "no matching candidate for image URI u'foo.*'" in app._warning.content[-1]
    assert set(htmlbuilder.images.keys()) == set(['subdir/img.png', 'img.png'])
    assert set(htmlbuilder.images.values()) == set(['img.png', 'img1.png'])

    app._warning.reset()
    latexbuilder = LaTeXBuilder(app, env)
    latexbuilder.post_process_images(tree)
    assert "no matching candidate for image URI u'foo.*'" in app._warning.content[-1]
    assert set(latexbuilder.images.keys()) == set(['subdir/img.png', 'img.png', 'img.pdf'])
    assert set(latexbuilder.images.values()) == set(['img.pdf', 'img.png', 'img1.png'])

def test_second_update():
    # delete, add and "edit" (change saved mtime) some files and update again
    env.all_docs['contents'] = 0
    root = path(app.srcdir)
    (root / 'images.txt').unlink()
    (root / 'new.txt').write_text('New file\n========\n')
    it = env.update(app.config, app.srcdir, app.doctreedir, app)
    msg = it.next()
    assert '1 added, 1 changed, 1 removed' in msg
    docnames = set()
    for docname in it:
        docnames.add(docname)
    assert docnames == set(['contents', 'new'])
    assert 'images' not in env.all_docs
    assert 'images' not in env.found_docs
