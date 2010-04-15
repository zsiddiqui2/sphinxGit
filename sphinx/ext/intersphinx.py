# -*- coding: utf-8 -*-
"""
    sphinx.ext.intersphinx
    ~~~~~~~~~~~~~~~~~~~~~~

    Insert links to objects documented in remote Sphinx documentation.

    This works as follows:

    * Each Sphinx HTML build creates a file named "objects.inv" that contains a
      mapping from object names to URIs relative to the HTML set's root.

    * Projects using the Intersphinx extension can specify links to such mapping
      files in the `intersphinx_mapping` config value.  The mapping will then be
      used to resolve otherwise missing references to objects into links to the
      other documentation.

    * By default, the mapping file is assumed to be at the same location as the
      rest of the documentation; however, the location of the mapping file can
      also be specified individually, e.g. if the docs should be buildable
      without Internet access.

    :copyright: Copyright 2007-2010 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import time
import zlib
import urllib2
import posixpath
from os import path

from docutils import nodes

from sphinx.builders.html import INVENTORY_FILENAME

handlers = [urllib2.ProxyHandler(), urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler()]
if hasattr(urllib2, 'HTTPSHandler'):
    handlers.append(urllib2.HTTPSHandler)

urllib2.install_opener(urllib2.build_opener(*handlers))


def read_inventory_v1(f, uri, join):
    invdata = {}
    line = f.next()
    projname = line.rstrip()[11:].decode('utf-8')
    line = f.next()
    version = line.rstrip()[11:]
    for line in f:
        name, type, location = line.rstrip().split(None, 2)
        location = join(uri, location)
        # version 1 did not add anchors to the location
        if type == 'mod':
            type = 'py:module'
            location += '#module-' + name
        else:
            type = 'py:' + type
            location += '#' + name
        invdata.setdefault(type, {})[name] = (projname, version, location)
    return invdata


def read_inventory_v2(f, uri, join, bufsize=16*1024):
    invdata = {}
    line = f.readline()
    projname = line.rstrip()[11:].decode('utf-8')
    line = f.readline()
    version = line.rstrip()[11:]
    line = f.readline()
    if 'zlib' not in line:
        raise ValueError

    def read_chunks():
        decompressor = zlib.decompressobj()
        for chunk in iter(lambda: f.read(bufsize), ''):
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def split_lines(iter):
        buf = ''
        for chunk in iter:
            buf += chunk
            lineend = buf.find('\n')
            while lineend != -1:
                yield buf[:lineend]
                buf = buf[lineend+1:]
                lineend = buf.find('\n')
        assert not buf

    for line in split_lines(read_chunks()):
        name, type, prio, location = line.rstrip().split(None, 3)
        if location.endswith('$'):
            location = location[:-1] + name
        location = join(uri, location)
        invdata.setdefault(type, {})[name] = (projname, version, location)
    return invdata


def fetch_inventory(app, uri, inv):
    """Fetch, parse and return an intersphinx inventory file."""
    # both *uri* (base URI of the links to generate) and *inv* (actual
    # location of the inventory file) can be local or remote URIs
    localuri = uri.find('://') == -1
    join = localuri and path.join or posixpath.join
    try:
        if inv.find('://') != -1:
            f = urllib2.urlopen(inv)
        else:
            f = open(path.join(app.srcdir, inv))
    except Exception, err:
        app.warn('intersphinx inventory %r not fetchable due to '
                 '%s: %s' % (inv, err.__class__, err))
        return
    try:
        line = f.readline().rstrip()
        try:
            if line == '# Sphinx inventory version 1':
                invdata = read_inventory_v1(f, uri, join)
            elif line == '# Sphinx inventory version 2':
                invdata = read_inventory_v2(f, uri, join)
            else:
                raise ValueError
            f.close()
        except ValueError:
            f.close()
            raise ValueError('unknown or unsupported inventory version')
    except Exception, err:
        app.warn('intersphinx inventory %r not readable due to '
                 '%s: %s' % (inv, err.__class__.__name__, err))
    else:
        return invdata


def load_mappings(app):
    """Load all intersphinx mappings into the environment."""
    now = int(time.time())
    cache_time = now - app.config.intersphinx_cache_limit * 86400
    env = app.builder.env
    if not hasattr(env, 'intersphinx_cache'):
        env.intersphinx_cache = {}
    cache = env.intersphinx_cache
    update = False
    for uri, inv in app.config.intersphinx_mapping.iteritems():
        # we can safely assume that the uri<->inv mapping is not changed
        # during partial rebuilds since a changed intersphinx_mapping
        # setting will cause a full environment reread
        if not inv:
            inv = posixpath.join(uri, INVENTORY_FILENAME)
        # decide whether the inventory must be read: always read local
        # files; remote ones only if the cache time is expired
        if '://' not in inv or uri not in cache \
               or cache[uri][0] < cache_time:
            invdata = fetch_inventory(app, uri, inv)
            cache[uri] = (now, invdata)
            update = True
    if update:
        env.intersphinx_inventory = {}
        for _, invdata in cache.itervalues():
            for type, objects in invdata.iteritems():
                env.intersphinx_inventory.setdefault(
                    type, {}).update(objects)


def missing_reference(app, env, node, contnode):
    """Attempt to resolve a missing reference via intersphinx references."""
    domain = node.get('refdomain')
    if not domain:
        # only objects in domains are in the inventory
        return
    target = node['reftarget']
    objtypes = env.domains[domain].objtypes_for_role(node['reftype'])
    if not objtypes:
        return
    for objtype in objtypes:
        fulltype = '%s:%s' % (domain, objtype)
        if fulltype in env.intersphinx_inventory and \
           target in env.intersphinx_inventory[fulltype]:
            break
    else:
        return
    proj, version, uri = env.intersphinx_inventory[fulltype][target]
    newnode = nodes.reference('', '')
    newnode['refuri'] = uri
    newnode['reftitle'] = '(in %s v%s)' % (proj, version)
    newnode['class'] = 'external-xref'
    newnode.append(contnode)
    return newnode


def setup(app):
    app.add_config_value('intersphinx_mapping', {}, True)
    app.add_config_value('intersphinx_cache_limit', 5, False)
    app.connect('missing-reference', missing_reference)
    app.connect('builder-inited', load_mappings)
