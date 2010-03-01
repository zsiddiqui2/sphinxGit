# -*- coding: utf-8 -*-
"""
    Sphinx
    ~~~~~~

    The Sphinx documentation toolchain.

    :copyright: Copyright 2007-2010 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys
from os import path

__version__ = '0.6.5+'
__released__ = '0.6.5'  # used when Sphinx builds its own docs

package_dir = path.abspath(path.dirname(__file__))

if '+' in __version__ or 'pre' in __version__:
    # try to find out the changeset hash if checked out from hg, and append
    # it to __version__ (since we use this value from setup.py, it gets
    # automatically propagated to an installed copy as well)
    try:
        import subprocess
        p = subprocess.Popen(['hg', 'id', '-i', '-R',
                              path.join(package_dir, '..')],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if out:
            __version__ += '/' + out.strip()
    except Exception:
        pass


def main(argv=sys.argv):
    if sys.version_info[:3] < (2, 4, 0):
        print >>sys.stderr, \
              'Error: Sphinx requires at least Python 2.4 to run.'
        return 1

    try:
        from sphinx import cmdline
    except ImportError, err:
        errstr = str(err)
        if errstr.lower().startswith('no module named'):
            whichmod = errstr[16:]
            hint = ''
            if whichmod.startswith('docutils'):
                whichmod = 'Docutils library'
            elif whichmod.startswith('jinja'):
                whichmod = 'Jinja library'
            elif whichmod == 'roman':
                whichmod = 'roman module (which is distributed with Docutils)'
                hint = ('This can happen if you upgraded docutils using\n'
                        'easy_install without uninstalling the old version'
                        'first.')
            else:
                whichmod += ' module'
            print >>sys.stderr, ('Error: The %s cannot be found. '
                                 'Did you install Sphinx and its dependencies '
                                 'correctly?' % whichmod)
            if hint:
                print >> sys.stderr, hint
            return 1
        raise
    return cmdline.main(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
