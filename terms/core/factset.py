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

from sqlalchemy import Table, Column, Sequence, Index
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError

from terms.core import exceptions
from terms.core.terms import get_bases
from terms.core.terms import Base, Term, Predicate
from terms.core.terms import isa, are
from terms.core.utils import Match


class FactSet(object):
    """
    """

    def __init__(self, name, lexicon, config):
        self.config = config
        self.session = lexicon.session
        self.lexicon = lexicon

    def get_paths(self, pred):
        '''
        build a path for each testable feature in term.
        Each path is a tuple of strings,
        and corresponds to a node in the primary network.
        '''
        paths = []
        self._recurse_paths(pred, paths, ())
        return paths

    def _recurse_paths(self, pred, paths, path):
        paths.append(path + ('_verb',))
        paths.append(path + ('_neg',))
        for label in sorted(pred.objects):
            o = pred.objects[label].value
            if isa(o, self.lexicon.exists):
                self._recurse_paths(o, paths, path + (label,))
            elif isa(o, self.lexicon.word):
                paths.append(path + (label, '_term'))

    def _get_nclass(self, path):
        ntype = path[-1]
        mapper = Segment.__mapper__
        return mapper.base_mapper.polymorphic_map[ntype].class_

    def add_fact(self, pred):
        fact = Fact(pred)
        paths = self.get_paths(pred)
        for n, path in enumerate(paths):
            cls = self._get_nclass(path)
            value = cls.resolve(pred, path, self)
            cls(fact, value, n)
        self.session.add(fact)
        self.session.commit()
        return fact

    def query(self, pred):
        paths = self.get_paths(pred)
        qfacts = self.session.query(Fact)
        vars = []
        for n, path in enumerate(paths):
            cls = self._get_nclass(path)
            value = cls.resolve(pred, path, self)
            qfacts = cls.filter_segment(qfacts, value, n, vars, path)
        sec_vars = []
        taken_vars = {}
        for var in vars:
            qfacts = var['cls'].filter_segment_first_var(qfacts, var['value'], var['n'], var['path'], self, taken_vars, sec_vars)
        for var in sec_vars:
            qfacts = var['cls'].filter_segment_sec_var(qfacts, var['n'], var['first'])
        matches = []
        for fact in qfacts:
            match = Match(fact.pred, query=pred)
            match.paths = paths
            match.fact = fact
            for name, path in taken_vars.items():
                cls = self._get_nclass(path)
                value = cls.resolve(fact.pred, path, self)
                match[name] = value
            matches.append(match)
        return matches


class Fact(Base):
    __tablename__ = 'facts'

    id = Column(Integer, Sequence('fact_id_seq'), primary_key=True)
    pred_id = Column(Integer, ForeignKey('predicates.id'), index=True)
    pred = relationship('Predicate', backref=backref('facts'),
                         cascade='all',
                         primaryjoin="Predicate.id==Fact.pred_id")
    
    def __init__(self, pred):
        self.pred = pred


class Segment(Base):
    __tablename__ = 'segments'

    id = Column(Integer, Sequence('segment_id_seq'), primary_key=True)
    fact_id = Column(Integer, ForeignKey('facts.id'), index=True)
    fact = relationship('Fact',
                         backref='segments',
                         primaryjoin="Fact.id==Segment.fact_id")
    order = Column(Integer, index=True)

    ntype = Column(String(5))
    __mapper_args__ = {'polymorphic_on': ntype}

    def __init__(self, fact, value, order):
        self.fact = fact
        self.value = value
        self.order = order

    @classmethod
    def filter_segment(cls, qfact, value, n, vars, path):
        if getattr(value, 'var', False):
            vars.append({'cls': cls, 'value': value, 'n': n, 'path': path})
        else:
            alias = aliased(cls)
            qfact = qfact.join(alias, Fact.id==alias.fact_id).filter(alias.value==value, alias.order==n)
        return qfact

    @classmethod
    def resolve(cls, pred, path, factset):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        raise NotImplementedError


class NegSegment(Segment):

    __mapper_args__ = {'polymorphic_identity': '_neg'}
    __table_args__ = {'extend_existing': True}
    value = Column(Boolean, index=True)
    
    @classmethod
    def resolve(cls, pred, path, factset):
        try:
            for segment in path[:-1]:
                pred = pred.get_object(segment)
            return pred.true
        except AttributeError:
            return None


class TermSegment(Segment):
    
    __mapper_args__ = {'polymorphic_identity': '_term'}
    __table_args__ = {'extend_existing': True}
    term_id = Column(Integer, ForeignKey('terms.id'), index=True)
    value = relationship('Term',
                         primaryjoin="Term.id==TermSegment.term_id")
    
    @classmethod
    def resolve(cls, term, path, factset):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        try:
            for segment in path[:-1]:
                term = term.get_object(segment)
        except (KeyError, AttributeError):
            return None
        return term

    @classmethod
    def filter_segment_first_var(cls, qfacts, value, n, path, factset, taken_vars, sec_vars):
        salias = aliased(cls)
        talias = aliased(Term)
        if value.name in taken_vars:
            sec_vars.append({'cls': cls, 'n': n, 'first': salias})
            return qfacts
        else:
            taken_vars[value.name] = path
        if value.bases:
            sbases = factset.lexicon.get_subterms(get_bases(value)[0])
        else:
            sbases = (value.term_type,) + factset.lexicon.get_subterms(value.term_type)
        sbases = (b.id for b in sbases)
        qfacts = qfacts.join(salias, Fact.id==salias.fact_id).filter(salias.order==n).join(talias, salias.term_id==talias.id).filter(talias.type_id.in_(sbases))
        return qfacts

    @classmethod
    def filter_segment_sec_var(cls, qfacts, n, salias):
        alias = aliased(cls)
        qfacts = qfacts.join(alias, Fact.id==alias.fact_id).filter(alias.order==n, alias.term_id==salias.term_id)
        return qfacts


class VerbSegment(Segment):

    __mapper_args__ = {'polymorphic_identity': '_verb'}
    __table_args__ = {'extend_existing': True}
    verb_id = Column(Integer, ForeignKey('terms.id'), index=True)
    value = relationship('Term',
                         primaryjoin="Term.id==VerbSegment.verb_id")
    
    @classmethod
    def resolve(cls, term, path, factset):
        try:
            for segment in path[:-1]:
                term = term.get_object(segment)
        except AttributeError:
            return None
        if term.var:
            return term
        return term.term_type

    @classmethod
    def filter_segment_first_var(cls, qfacts, value, n, path, factset, taken_vars, sec_vars):
        salias = aliased(cls)
        talias = aliased(Term)
        if value.name in taken_vars:
            sec_vars.append({'cls': cls, 'n': n, 'first': salias})
            return
        else:
            taken_vars[value.name] = path
        if isa(value, factset.lexicon.verb):
            sbases = factset.lexicon.get_subterms(get_bases(value)[0])
        elif isa(value, factset.lexicon.exists):
            sbases = factset.lexicon.get_subterms(value.term_type)
        sbases = (b.id for b in sbases)
        qfacts = qfacts.join(salias, Fact.id==salias.fact_id).filter(salias.order==n).join(talias, salias.verb_id==talias.id).filter(talias.id.in_(sbases))
        return qfacts

    @classmethod
    def filter_segment_sec_var(cls, qfatcs, n, salias):
        alias = aliased(cls)
        qfacts = qfacts.join(alias, Fact.id==alias.fact_id).filter(alias.order==n, alias.varb_id==salias.verb_id)
        return qfacts


ancestor_child = Table('ancestor_child', Base.metadata,
    Column('ancestor_id', Integer, ForeignKey('ancestors.id'), index=True),
    Column('child_id', Integer, ForeignKey('facts.id'), index=True)
)

ancestor_parent = Table('ancestor_parent', Base.metadata,
    Column('ancestor_id', Integer, ForeignKey('ancestors.id'), index=True),
    Column('parent_id', Integer, ForeignKey('facts.id'), index=True)
)

class Ancestor(Base):
    __tablename__ = 'ancestors'

    id = Column(Integer, Sequence('ancestor_id_seq'), primary_key=True)
    children = relationship('Fact', backref='ancestors',
                         secondary=ancestor_child,
                         primaryjoin=id==ancestor_child.c.ancestor_id,
                         secondaryjoin=Fact.id==ancestor_child.c.child_id)
    parents = relationship('Fact', backref=backref('descent', cascade='all'),
                         secondary=ancestor_parent,
                         primaryjoin=id==ancestor_parent.c.ancestor_id,
                         secondaryjoin=Fact.id==ancestor_parent.c.parent_id)

    def __init__(self, fact=None):
        if fact:
            self.parents.append(fact)


    def copy(self):
        new = Ancestor()
        for p in self.parents:
            new.parents.append(p)
        return new
