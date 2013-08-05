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

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from terms.core import exceptions
from terms.core import patterns
from terms.core.terms import Term, Predicate, isa, are, Time


class Lexicon(object):

    def __init__(self, session, config):
        self.config = config
        self.session = session
        self.word = self.get_term('word')
        self.verb = self.get_term('verb')
        self.noun = self.get_term('noun')
        self.number = self.get_term('number')
        self.exist = self.get_term('exist')
        self.endure = self.get_term('endure')
        self.exclusive_endure = self.get_term('exclusive-endure')
        self.occur = self.get_term('occur')
        self.happen = self.get_term('happen')
        self.vtime = self.get_term('time')
        self.thing = self.get_term('thing')
        self.finish = self.get_term('finish')
        self.time = self.session.query(Time).one()
        self.now_term = self.make_term(str(0 + self.time.now), self.number)
        self._term_cache = {}

    @classmethod
    def initialize(cls, session):
        '''
        Create basic terms.
        '''
        word = Term('word', _bootstrap=True)
        session.add(word)
        session.commit()
        word.term_type = word
        session.commit()
        verb = Term('verb', ttype=word, bases=(word,))
        session.add(verb)
        noun = Term('noun', ttype=word, bases=(word,))
        session.add(noun)
        number = Term('number', ttype=word, bases=(word,))
        session.add(number)
        exist = Term('exist', ttype=verb, bases=(word,),
                      objs={'subj': word})
        session.add(exist)
        endure = Term('endure', ttype=verb, bases=(exist,),
                       objs={'since_': number, 'till_': number})
        session.add(endure)
        exclusive_endure = Term('exclusive-endure', ttype=verb, bases=(endure,))
        session.add(exclusive_endure)
        occur = Term('occur', ttype=verb, bases=(exist,),
                   objs={'at_': number})
        session.add(occur)
        happen = Term('happen', ttype=verb, bases=(occur,))
        session.add(happen)
        time = Term('time', ttype=verb, bases=(exist,),
                    objs={'subj': number})
        session.add(time)
        thing = Term('thing', ttype=noun, bases=(word,))
        session.add(thing)
        finish = Term('finish', ttype=verb, bases=(occur,),
                      objs={'subj': thing, 'what': exist})
        session.add(finish)
        time = Time()
        session.add(time)
        session.commit()

    def get_term(self, name):
        '''
        Given a name (string), get a Term from the database.
        The Term must exist.
        '''
        cache = getattr(self, '_term_cache', None)
        if cache is not None:
            if name in cache:
                return cache[name]
        else:
            self._term_cache = {}
        try:
            return self.session.query(Term).filter_by(name=name).one()
        except MultipleResultsFound:
            raise exceptions.TermRepeated(name)
        except NoResultFound:
            raise exceptions.TermNotFound(name)

    def get_terms(self, term_type):
        '''
        Get all terms of type term_type.
        The term_type must exist.
        '''
        types = self.get_subterms(term_type)
        type_ids = [t.id for t in types if t is not self.number]
        return self.session.query(Term).filter(Term.type_id.in_(type_ids)).all()

    def make_term(self, name, term_type, **objs):
        '''
        Make a Term from a name (string) and a term_type (Term).
        Can also produce a predicate.
        The term is not saved or added to the session.
        '''
        try:
            return self.get_term(name)
        except exceptions.TermNotFound:
            if are(term_type, self.noun):
                return self._make_noun(name, ntype=term_type)
            elif are(term_type, self.thing):
                return self._make_name(name, term_type)
            elif are(term_type, self.verb):
                return self._make_verb(name, vtype=term_type, objs=objs)
            elif are(term_type, self.exist):
                return self.make_pred(name, term_type, **objs)
            elif term_type == self.number:
                return self.make_number(name)
            else:
                return Term(name, ttype=term_type)

    def make_subterm(self, name, super_terms, **objs):
        '''
        Make a Term from a name (string) and bases (Term's).
        The bases are the supertypes of a type,
        and can be a tuple of terms or a single term.
        The term is not saved or added to the session.
        '''
        try:
            return self.get_term(name)
        except exceptions.TermNotFound:
            if isa(super_terms, self.word):
                super_terms = (super_terms,)
            term_base = super_terms[0]
            if are(term_base, self.noun):
                return self._make_subnoun(name, bases=super_terms)
            elif are(term_base, self.thing):
                return self._make_noun(name, bases=super_terms)
            elif are(term_base, self.verb):
                return self._make_subverb(name, bases=super_terms)
            elif are(term_base, self.exist):
                return self._make_verb(name, bases=super_terms, objs=objs)

    def add_term(self, name, term_type, **objs):
        term = self.make_term(name, term_type, **objs)
        self.session.add(term)
        term.purge_cache(self)
        self._term_cache[name] = term
        return term

    def add_subterm(self, name, super_terms, **objs):
        term = self.make_subterm(name, super_terms, **objs)
        self.session.add(term)
        term.purge_cache(self)
        self._term_cache[name] = term
        return term

    def get_subterms(self, term):
        cache = getattr(term, '_sub_cache', None)
        if cache is not None:
            return cache
        name = term.name
        m = patterns.varpat.match(name)
        if m:
            if m.group(2):
                term = self.get_term(m.group(1).lower())
            else:
                return ()
        subtypes = set([term])
        self._recurse_subterms(term, subtypes)
        subterms = tuple(subtypes)
        term._sub_cache = subterms
        return subterms

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
            if len(tname) == 1:
                tvar = self.number
            else:
                tvar = self.get_term(tname)
            if isa(tvar, self.verb) or tvar == self.number:
                var = Term(name, ttype=tvar)
            else:
                var = self.make_term(name, tvar)
        var.var = True
        self.session.add(var)
        return var

    def _recurse_subterms(self, term, subterms):
        for st in term.subwords:
            if st.var:
                continue
            subterms.add(st)
            self._recurse_subterms(st, subterms)

    def _make_noun(self, name, bases=None, ntype=None):
        if bases is None:
            bases = (self.thing,)
        elif isa(bases, self.word):
            bases = (bases,)
        if ntype is None:
            ntype = self.noun
        return Term(name, ttype=ntype, bases=tuple(bases))

    def _make_subnoun(self, name, bases=None):
        if bases is None:
            bases = (self.noun,)
        return Term(name, ttype=self.word, bases=tuple(bases))

    def _make_name(self, name, noun_):
        return Term(name, ttype=noun_)

    def _make_verb(self, name, bases=None, vtype=None, objs=None):
        if objs is None:
            objs = {}
        for l in objs:
            if '_' in l:
                raise exceptions.IllegalLabel(l)
        if vtype is None:
            vtype = bases[0].term_type
        return Term(name, ttype=vtype, bases=tuple(bases), objs=objs)

    def _make_subverb(self, name, bases=None):
        return Term(name, ttype=self.word, bases=tuple(bases))

    def make_number(self, num):
        num = str(0 + eval(str(num), {}, {}))
        number = Term(num, ttype=self.number)
        number.number = True
        return number

    def make_pred(self, true, verb_, **objs):
        return Predicate(true, verb_, **objs)
