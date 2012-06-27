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

from terms.terms import Term, ObjectType
from terms import exceptions

NAME_PAT = re.compile(r'^([a-z][a-z_]*[a-z])[1-9]+$')


class Lexicon(object):

    def __init__(self, engine):
        Session = sessionmaker()
        Session.configure(bind=engine)
        self.session = Session()
        try:
            self.word = self.get_term('word')
            self.noun = self.get_term('noun')
            self.verb = self.get_term('verb')
            self.thing = self.get_term('thing')
            self.exists = self.get_term('exists')
        except exceptions.TermNotFound:
            self.word = Term('word', _bootstrap=True)
            self.session.add(word)
            self.noun = self.add_word('noun', word, _commit=False)
            self.verb = self.add_word('verb', word, _commit=False)
            self.thing = self.add_word('thing', noun, _commit=False)
            self.exists = self.add_word('exists', verb, _commit=False)
            self.session.commit()

    def add_term(self, name, term_type, _commit=True, **objs):
        t = self.make_term(name, term_type, **objs)
        self.session.add(t)
        if _commit:
            self.session.commit()
        return t

    def add_subterm(self, name, super_terms, _commit=True, **objs):
        t = self.make_subterm(name, super_terms, **objs)
        self.session.add(t)
        if _commit:
            self.session.commit()
        return t

    def get_term(self, name):
        # cache
        try:
            return self.session.query(Term).filter_by(name=name).one()
        except MultipleResultsFound:
            raise exceptions.TermRepeated()
        except NoResultFound:
            raise exceptions.TermNotFound()

    def make_term(self, name, term_type, **objs):
        if term_type.are(self.get_term('noun')):
            return self._make_noun(name, ntype=term_type)
        elif term_type.are(self.get_term('thing')):
            return self._make_name(name, term_type)
        elif term_type.are(self.get_term('verb')):
            return self._make_verb(name, vtype=term_type, **objs)

    def make_subterm(self, name, super_terms, **objs):
        if super_terms.isa(self.get_term('word')):
            super_terms = (super_terms,)
        term_base = super_terms[0]
        if term_base.are(self.get_term('noun')):
            return self._make_noun(name, bases=super_terms)
        elif term_base.are(self.get_term('thing')):
            return self._make_noun(name, bases=super_terms)
        elif term_base.are(self.get_term('verb')):
            return self._make_verb(name, bases=super_terms)
        elif term_base.are(self.get_term('exists')):
            return self._make_verb(name, bases=super_terms, **objs)

    def _make_noun(self, name, bases=None, ntype=None):
        if bases is None:
            bases = (self.get_term('thing'),)
        elif isinstance(bases, Term):
            bases = (bases,)
        if ntype is None:
            ntype = self.get_term('noun')
        new = Term(name, ttype=ntype, bases=bases)
        return new

    def _make_name(self, name, noun):
        return Term(name, ttype=noun)

    def _make_verb(self, name, bases=None, vtype=None, **objs):
        if bases is None:
            bases = (self.get_term('exists'),)
        elif isinstance(bases, Term):
            bases = (bases,)
        if vtype is None:
            if bases:
                vtype = bases[0].term_type
            else:
                vtype = self.get_term('verb')
        objects = []
        for label, obj_type in objs.items():
            objects.append(ObjectType(label, obj_type))
        for base in bases:
            if hasattr(base, 'objs'):
                objects += base.objs
        new = Term(name, ttype=vtype, bases=bases, objs=objects)
        return new

    def _make_subverb(self, name, bases=None):
        if bases is None:
            bases = (self.get_term('verb'),)
        new = Term(name, ttype=self.get_term('word'), bases=tuple(bases))
        return new

    def _make_subnoun(self, name, bases=None):
        if bases is None:
            bases = (self.get_term('noun'),)
        new = Term(name, ttype=self.get_term('word'), bases=tuple(bases))
        return new
