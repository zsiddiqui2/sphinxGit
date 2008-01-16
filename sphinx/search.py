# -*- coding: utf-8 -*-
"""
    sphinx.search
    ~~~~~~~~~~~~~

    Create a search index for offline search.

    :copyright: 2007-2008 by Armin Ronacher.
    :license: BSD.
"""
import re
import pickle

from docutils.nodes import Text, NodeVisitor

from sphinx.util.stemmer import PorterStemmer
from sphinx.util.json import dump_json, load_json


word_re = re.compile(r'\w+(?u)')


class Stemmer(PorterStemmer):
    """
    All those porter stemmer implementations look hideous.
    make at least the stem method nicer.
    """

    def stem(self, word):
        return PorterStemmer.stem(self, word, 0, len(word) - 1)


class WordCollector(NodeVisitor):
    """
    A special visitor that collects words for the `IndexBuilder`.
    """

    def __init__(self, document):
        NodeVisitor.__init__(self, document)
        self.found_words = []

    def dispatch_visit(self, node):
        if node.__class__ is Text:
            self.found_words.extend(word_re.findall(node.astext()))


class IndexBuilder(object):
    """
    Helper class that creates a searchindex based on the doctrees
    passed to the `feed` method.
    """
    formats = {
        'json':     (dump_json, load_json),
        'pickle':   (pickle.dumps, pickle.loads),
    }

    def __init__(self):
        self._stemmer = Stemmer()
        # filename -> title
        self._titles = {}
        # stemmed word -> set(filenames)
        self._mapping = {}

    def load(self, stream, format):
        """Reconstruct from frozen data."""
        frozen = self.formats[format][1](stream.read())
        index2fn = frozen[0]
        self._titles = dict(zip(frozen[0], frozen[1]))
        self._mapping = dict((k, set(index2fn[i] for i in v))
                             for (k, v) in frozen[2].iteritems())

    def dump(self, stream, format):
        """Dump the frozen index to a stream."""
        stream.write(self.formats[format][0](self.freeze()))

    def freeze(self):
        """
        Create a useable data structure. You can pass this output
        to the `SearchFrontend` to search the index.
        """
        fns, titles = self._titles.keys(), self._titles.values()
        fn2index = dict((f, i) for (i, f) in enumerate(fns))
        return [
            fns,
            titles,
            dict((k, [fn2index[fn] for fn in v])
                 for (k, v) in self._mapping.iteritems()),
        ]

    def prune(self, filenames):
        """Remove data for all filenames not in the list."""
        new_titles = {}
        for filename in filenames:
            if filename in self._titles:
                new_titles[filename] = self._titles[filename]
        self._titles = new_titles
        for wordnames in self._mapping.itervalues():
            wordnames.intersection_update(filenames)

    def feed(self, filename, title, doctree):
        """Feed a doctree to the index."""
        self._titles[filename] = title

        visitor = WordCollector(doctree)
        doctree.walk(visitor)
        for word in word_re.findall(title) + visitor.found_words:
            self._mapping.setdefault(self._stemmer.stem(word.lower()),
                                     set()).add(filename)


class SearchFrontend(object):
    """
    This class acts as a frontend for the search index. It can search
    a searchindex as provided by `IndexBuilder`.
    """

    def __init__(self, index):
        self.filenames, self.titles, self.words = index
        self._stemmer = Stemmer()

    def query(self, required, excluded):
        file_map = {}
        for word in required:
            if word not in self.words:
                break
            for fid in self.words[word]:
                file_map.setdefault(fid, set()).add(word)

        return sorted(((self.filenames[fid], self.titles[fid])
            for fid, words in file_map.iteritems()
            if len(words) == len(required) and not
               any(fid in self.words.get(word, ()) for word in excluded)
        ), key=lambda x: x[1].lower())

    def search(self, searchstring):
        required = set()
        excluded = set()
        for word in searchstring.split():
            if word.startswith('-'):
                storage = excluded
                word = word[1:]
            else:
                storage = required
            storage.add(self._stemmer.stem(word.lower()))

        return self.query(required, excluded)
