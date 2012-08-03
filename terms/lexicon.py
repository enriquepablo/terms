# Copyright (c) 2007-2012 by Enrique Pérez Arnaud <enriquepablo@gmail.com>
#
# This file is part of the terms project.
# https://github.com/enriquepablo/terms
#
# The terms project is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The terms project is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with any part of the terms project.
# If not, see <http://www.gnu.org/licenses/>.

import re

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm import sessionmaker

from terms import exceptions
from terms import patterns
from terms.words import word, noun, thing, verb, exists, isa, are
from terms.words import get_name, get_type, get_bases
from terms.terms import Term, ObjectType
from terms.utils import Match, merge_submatches


class Lexicon(object):

    def __init__(self, session):
        self.session = session
        self.words = {'word': word,
                      'noun': noun,
                      'verb': verb,
                      'thing': thing,
                      'exists': exists}
        wrd = Term('word', _bootstrap=True)
        self.session.add(wrd)
        self.add_word('noun', word, _commit=False)
        self.add_word('verb', word, _commit=False)
        self.add_word('thing', noun, _commit=False)
        self.add_word('exists', verb, _commit=False)
        self.session.commit()

    def make_word(self, name, word_type, **objs):
        if name in self.words:
            return self.words[name]
        if are(word_type, noun):
            return self._make_noun(name, ntype=word_type)
        elif are(word_type, thing):
            return self._make_name(name, word_type)
        elif are(word_type, verb):
            return self._make_verb(name, vtype=word_type, objs=objs)

    def make_subword(self, name, super_words, **objs):
        if isa(super_words, word):
            super_words = (super_words,)
        for super_word in super_words:
            super_name = get_name(super_word)
            if hasattr(super_word, 'objs'):
                objs.update(super_word.objs)
        word_base = super_words[0]
        if are(word_base, noun):
            return self._make_subnoun(name, bases=super_words)
        elif are(word_base, thing):
            return self._make_noun(name, bases=super_words)
        elif are(word_base, verb):
            return self._make_subverb(name, bases=super_words)
        elif are(word_base, exists):
            return self._make_verb(name, bases=super_words, objs=objs)

    def make_var(self, name):
        m = patterns.varpat.match(name)
        if m.group(2):
            base = m.group(1).lower()
            bases = [self.get_word(base)]
            return self.make_subword(name, bases)
        tname = m.group(1).lower()
        tvar = self.get_word(tname)
        return self.make_word(name, tvar)

    def save_word(self, w, _commit=True):
        name = get_name(w)
        word_type = get_type(w)
        self.words[name] = w
        try:
            term = self.get_term(name)
        except exceptions.TermNotFound:
            pass
        else:
            if term:
                raise exceptions.TermRepeated(name)
        objects = []
        if hasattr(w, 'objs'):
            for label, obj_type in w.objs.items():
                obj_tname = get_name(obj_type)
                obj_term = self.get_term(obj_tname)
                objects.append(ObjectType(label, obj_term))
        term_type = self.get_term(get_name(word_type))
        bases = get_bases(w)
        bases = [self.get_term(get_name(b)) for b in bases]
        term = Term(name, ttype=term_type, bases=bases, objs=objects)
        self.session.add(term)
        if _commit:
            self.session.commit()
        return term

    def add_word(self, name, word_type, _commit=True, **objs):
        w = self.make_word(name, word_type, **objs)
        self.save_word(w, _commit=_commit)
        return w


    def add_subword(self, name, super_words, _commit=True, **objs):
        w = self.make_subword(name, super_words, **objs)
        self.save_word(w, _commit=_commit)
        return w

    def get_word(self, name):
        try:
            return self.words[name]
        except KeyError:
            term = self.get_term(name)
            if term.bases:
                bases = []
                for b in term.bases:
                    base = self.get_word(b.name)
                    bases.append(base)
                w = self.make_subword(name, bases)
            else:
                word_type = self.words[term.term_type.name]
                w = self.make_word(name, word_type)
            self.words[name] = w
            return w

    def get_subwords(self, w):
        term = self.get_term(get_name(w))
        subtypes = []
        self._recurse_subterms(term, subtypes)
        subtypes = [] + [self.get_word(t.name) for t in subtypes]
        return tuple(subtypes)

    def _recurse_subterms(self, term, subterms):
        sterms = term.subwords
        for st in sterms:
            if st not in subterms:
                subterms.append(st)
                self._recurse_subterms(st, subterms)

    def get_term(self, name):
        try:
            return self.session.query(Term).filter_by(name=name).one()
        except MultipleResultsFound:
            raise exceptions.TermRepeated()
        except NoResultFound:
            raise exceptions.TermNotFound()

    def _load_terms(self):
        terms = self.session.query(Term).all()
        for term in terms:
            type_name = term.types[0].name
            term_type = self.words[type_name]
            if not issubclass(term_type, thing):
                term_types = [self.words[ttype.name] for ttype in term.types]
                if issubclass(term_type, noun):
                    self._make_noun(type_name, term_types)
                elif issubclass(term_type, verb):
                    objects = dict([(obj.label, self.words[obj.term_type.name])
                                                for obj in term.object_types])
                    self._make_verb(type_name, term_types, objects)

    def _make_noun(self, name, bases=None, ntype=None):
        if bases is None:
            bases = (thing,)
        elif isinstance(bases, word):
            bases = (bases,)
        if ntype is None:
            ntype = noun
        new = ntype(name, tuple(bases), {})
        return new

    def _make_name(self, name, noun_=None):
        if noun_ is None:
            m = patterns.NAME_PAT.match(name)
            if m:
                noun_ = self.words[m.group(1)]
                assert isinstance(noun_, noun)
            else:
                noun_ = thing
        new = noun_(name)
        return new

    def _make_verb(self, name, bases=None, vtype=None, objs=None):
        if bases is None:
            bases = (exists,)
        elif bases is None:
            bases = ()
        elif isinstance(bases, verb):
            bases = (bases,)
        if objs is None:
            objs = {}
        if vtype is None:
            if bases:
                vtype = type(bases[0])
            else:
                vtype = verb
        new = vtype(name, tuple(bases), objs)
        return new

    def _make_subverb(self, name, bases=None):
        if bases is None:
            bases = (verb,)
        new = word(name, tuple(bases), {})
        return new

    def _make_subnoun(self, name, bases=None):
        if bases is None:
            bases = (noun,)
        new = word(name, tuple(bases), {})
        return new
