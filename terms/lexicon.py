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
from terms.terms import get_bases
from terms.terms import Term, ObjectType, Predicate, isa, are
from terms.utils import Match, merge_submatches


class Lexicon(object):

    def __init__(self, session):
        self.session = session
        try:
            self.session.query(Term).filter(Term.name=='word').one()
        except NoResultFound:
            self.initialize()

    def initialize(self):
        '''
        Create basic terms.
        '''
        word = Term('word', _bootstrap=True)
        self.session.add(word)
        self.session.commit()
        word.term_type = word
        self.session.commit()
        verb = Term('verb', ttype=word, bases=(word,))
        self.session.add(verb)
        noun = Term('noun', ttype=word, bases=(word,))
        self.session.add(noun)
        exists = Term('exists', ttype=verb, objs={'subj': word})
        self.session.add(exists)
        thing = Term('thing', ttype=noun, bases=(word,))
        self.session.add(thing)
        self.session.commit()

    def get_term(self, name):
        '''
        Given a name (string), get a Term from the database.
        The Term must exist.
        '''
        try:
            return self.session.query(Term).filter_by(name=name).one()
        except MultipleResultsFound:
            raise exceptions.TermRepeated(name)
        except NoResultFound:
            raise exceptions.TermNotFound(name)

    def make_term(self, name, term_type, **objs):
        '''
        Make a Term from a name (string) and a term_type (Term).
        Can also produce a predicate.
        The term is not saved or added to the session.
        '''
        verb = self.get_term('verb')
        noun = self.get_term('noun')
        exists = self.get_term('exists')
        thing = self.get_term('thing')
        try:
            return self.get_term(name)
        except exceptions.TermNotFound:
            pass
        if are(term_type, noun):
            return self._make_noun(name, ntype=term_type)
        elif are(term_type, thing):
            return self._make_name(name, term_type)
        elif are(term_type, verb):
            return self._make_verb(name, vtype=term_type, objs=objs)
        elif are(term_type, exists):
            return self.make_pred(name, term_type, **objs)

    def make_subterm(self, name, super_terms, **objs):
        '''
        Make a Term from a name (string) and bases (Term's).
        The bases are the supertypes of a type,
        and can be a tuple of terms or a single term.
        The term is not saved or added to the session.
        '''
        word = self.get_term('word')
        verb = self.get_term('verb')
        noun = self.get_term('noun')
        exists = self.get_term('exists')
        thing = self.get_term('thing')
        try:
            return self.get_term(name)
        except exceptions.TermNotFound:
            pass
        if isa(super_terms, word):
            super_terms = (super_terms,)
        term_base = super_terms[0]
        if are(term_base, noun):
            return self._make_subnoun(name, bases=super_terms)
        elif are(term_base, thing):
            return self._make_noun(name, bases=super_terms)
        elif are(term_base, verb):
            return self._make_subverb(name, bases=super_terms)
        elif are(term_base, exists):
            return self._make_verb(name, bases=super_terms, objs=objs)

    def save_term(self, term, _commit=True):
        self.session.add(term)
        if _commit:
            self.session.commit()
        return term

    def add_term(self, name, term_type, _commit=False, **objs):
        try:
            pterm = self.get_term(name)
        except exceptions.TermNotFound:
            pass
        term = self.make_term(name, term_type, **objs)
        self.save_term(term, _commit)

    def add_subterm(self, name, super_terms, _commit=False, **objs):
        try:
            pterm = self.get_term(name)
        except exceptions.TermNotFound:
            pass
        term = self.make_subterm(name, super_terms, **objs)
        self.save_term(term, _commit)

    def get_subterms(self, term):
        name = term.name
        m = patterns.varpat.match(name)
        if m:
            if m.group(2):
                term = self.get_term(m.group(1).lower())
            else:
                return ()
        subtypes = [term]
        self._recurse_subterms(term, subtypes)
        return tuple(subtypes)

    def make_var(self, name):
        '''
        Make a term that represents a variable in a rule or query.
        It is not added to the session.
        Its name has the original trailing digits.
        
        '''
        try:
            return self.get_term(name)
        except exceptions.TermNotFound:
            pass
        m = patterns.varpat.match(name)
        if m.group(2):
            basename = m.group(1).lower()
            bases = self.get_term(basename)
            var = self.make_subterm(name, bases)
        else:
            tname = m.group(1).lower()
            tvar = self.get_term(tname)
            verb = self.get_term('verb')
            if isa(tvar, verb):
                var = self._make_name(name, tvar)
            else:
                var = self.make_term(name, tvar)
        var.var = True
        self.session.add(var)
        return var

    def _recurse_subterms(self, term, subterms):
        sterms = term.subwords
        for st in sterms:
            if st not in subterms:
                subterms.append(st)
                self._recurse_subterms(st, subterms)

    def _make_noun(self, name, bases=None, ntype=None):
        word = self.get_term('word')
        noun = self.get_term('noun')
        thing = self.get_term('thing')
        if bases is None:
            bases = (thing,)
        elif isa(bases, word):
            bases = (bases,)
        if ntype is None:
            ntype = noun
        return Term(name, ttype=ntype, bases=tuple(bases))

    def _make_subnoun(self, name, bases=None):
        word = self.get_term('word')
        noun = self.get_term('noun')
        if bases is None:
            bases = (noun,)
        return Term(name, ttype=word, bases=tuple(bases))

    def _make_name(self, name, noun_=None):
        if noun_ is None:
            noun = self.get_term('noun')
            thing = self.get_term('thing')
            m = patterns.NAME_PAT.match(name)
            if m:
                noun_ = self.get_term(m.group(1))
                assert isa(noun_, noun)
            else:
                noun_ = thing
        return Term(name, ttype=noun_)

    def _make_verb(self, name, bases=None, vtype=None, objs=None):
        verb = self.get_term('verb')
        exists = self.get_term('exists')
        if not bases:
            bases = (exists,)
        elif isa(bases, verb):
            bases = (bases,)
        if objs is None:
            objs = {}
        if vtype is None:
            if bases:
                vtype = bases[0].term_type
            else:
                vtype = verb
        return Term(name, ttype=vtype, bases=tuple(bases), objs=objs)

    def _make_subverb(self, name, bases=None):
        word = self.get_term('word')
        verb = self.get_term('verb')
        if bases is None:
            bases = (verb,)
        return Term(name, ttype=word, bases=tuple(bases))

    def make_pred(self, true, verb_, **objs):
        return Predicate(true, verb_, **objs)
