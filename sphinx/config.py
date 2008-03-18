# -*- coding: utf-8 -*-
"""
    sphinx.config
    ~~~~~~~~~~~~~

    Build configuration file handling.

    :copyright: 2008 by Georg Brandl.
    :license: BSD license.
"""

import os
import types
from os import path


class Config(object):
    """Configuration file abstraction."""

    # the values are: (default, needs fresh doctrees if changed)

    # If you add a value here, don't forget to include it in the
    # quickstart.py file template as well as in the docs!

    config_values = dict(
        # general substitutions
        project = ('Python', True),
        copyright = ('', False),
        version = ('', True),
        release = ('', True),
        today = ('', True),
        today_fmt = ('%B %d, %Y', True),

        # extensibility
        templates_path = ([], False),
        extensions = ([], True),

        # general reading options
        master_doc = ('contents', True),
        source_suffix = ('.rst', True),
        unused_docs = ([], True),
        add_function_parentheses = (True, True),
        add_module_names = (True, True),
        show_authors = (False, True),
        pygments_style = ('sphinx', False),

        # HTML options
        html_style = ('default.css', False),
        html_static_path = ([], False),
        html_last_updated_fmt = ('%b %d, %Y', False),
        html_use_smartypants = (True, False),
        html_translator_class = (None, False),
        html_index = ('', False),
        html_sidebars = ({}, False),
        html_additional_pages = ({}, False),
        html_use_modindex = (True, False),
        html_copy_source = (True, False),

        # HTML help options
        htmlhelp_basename = ('pydoc', False),

        # LaTeX options
        latex_paper_size = ('letter', False),
        latex_font_size = ('10pt', False),
        latex_documents = ([], False),
        latex_preamble = ('', False),
        latex_appendices = ([], False),
        latex_use_modindex = (True, False),
    )

    def __init__(self, dirname, filename):
        self.values = self.config_values.copy()
        config = {'__file__': path.join(dirname, filename)}
        olddir = os.getcwd()
        try:
            os.chdir(dirname)
            execfile(config['__file__'], config)
        finally:
            os.chdir(olddir)
        # remove potentially pickling-problematic values
        for key, val in config.items():
            if key.startswith('_') or isinstance(val, types.ModuleType):
                del config[key]
        self.__dict__.update(config)

    def init_defaults(self):
        for val in self.values:
            if val not in self.__dict__:
                self.__dict__[val] = self.values[val][0]

    def __getitem__(self, name):
        return getattr(self, name)

    def __contains__(self, name):
        return hasattr(self, name)
