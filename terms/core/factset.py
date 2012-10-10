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

from sqlalchemy import Table, Column, Sequence
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship, backref, aliased

from terms.core.terms import get_bases
from terms.core.terms import Base, Term
from terms.core.terms import isa
from terms.core.utils import Match


class FactSet(object):
    """
    """

    def __init__(self, name, lexicon, config):
        self.name = name
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

    def add_fact(self, pred, prev):
        if prev:
            return prev[0]
        fact = Fact(pred, self.name)
        paths = self.get_paths(pred)
        for path in paths:
            cls = self._get_nclass(path)
            value = cls.resolve(pred, path, self)
            cls(fact, value, path)
        self.session.add(fact)
        return fact

    def add_object_to_fact(self, fact, value, path):
        cls = self._get_nclass(path)
        segment = cls(fact, value, path)
        self.session.add(segment)
        fact.pred.add_object(path[-2], value)

    def query_facts(self, pred, taken_vars):
        vars = []
        sec_vars = []
        paths = self.get_paths(pred)
        qfacts = self.session.query(Fact).filter(Fact.factset==self.name)
        for path in paths:
            cls = self._get_nclass(path)
            value = cls.resolve(pred, path, self)
            if value is not None:
                qfacts = cls.filter_segment(qfacts, value, vars, path)
        for var in vars:
            qfacts = var['cls'].filter_segment_first_var(qfacts, var['value'], var['path'], self, taken_vars, sec_vars)
        for var in sec_vars:
            qfacts = var['cls'].filter_segment_sec_var(qfacts, var['path'], var['first'])
        return qfacts

    def query(self, pred):
        taken_vars = {}
        qfacts = self.query_facts(pred, taken_vars)
        matches = []
        for fact in qfacts:
            match = Match(fact.pred, query=pred)
            match.fact = fact
            for name, path in taken_vars.items():
                cls = self._get_nclass(path[0])
                preds = True
                if 'Verb' in name[1:]:
                    preds = False
                value = cls.resolve(fact.pred, path[0], self, preds=preds)
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
    factset = Column(String(16))
    
    def __init__(self, pred, name):
        self.pred = pred
        self.factset = name

    def get_descent(self, descent=None):
        if descent is None:
            descent = [self]
        for d in self.descent:
            for fact in d.children:
                if fact is not self:
                    descent.append(fact)
                    fact.get_descent(descent)
        return descent


class Segment(Base):
    __tablename__ = 'segments'

    id = Column(Integer, Sequence('segment_id_seq'), primary_key=True)
    fact_id = Column(Integer, ForeignKey('facts.id'), index=True)
    fact = relationship('Fact',
                         backref='segments',
                         primaryjoin="Fact.id==Segment.fact_id")
    path = Column(String, index=True)

    ntype = Column(String(5))
    __mapper_args__ = {'polymorphic_on': ntype}

    def __init__(self, fact, value, path):
        self.fact = fact
        self.value = value
        self.path = '.'.join(path)

    @classmethod
    def filter_segment(cls, qfact, value, vars, path):
        if getattr(value, 'var', False):
            vars.append({'cls': cls, 'value': value, 'path': path})
        else:
            alias = aliased(cls)
            path_str = '.'.join(path)
            qfact = qfact.join(alias, Fact.id==alias.fact_id).filter(alias.value==value, alias.path==path_str)
        return qfact

    @classmethod
    def resolve(cls, pred, path, factset, preds=False):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        raise NotImplementedError


class NegSegment(Segment):

    __mapper_args__ = {'polymorphic_identity': '_neg'}
    value = Column(Boolean, index=True)
    
    @classmethod
    def resolve(cls, pred, path, factset, preds=False):
        try:
            for segment in path[:-1]:
                pred = pred.get_object(segment)
            return pred.true
        except AttributeError:
            return None


class TermSegment(Segment):
    
    __mapper_args__ = {'polymorphic_identity': '_term'}
    term_id = Column(Integer, ForeignKey('terms.id'), index=True)
    value = relationship('Term',
                         primaryjoin="Term.id==TermSegment.term_id")
    
    @classmethod
    def resolve(cls, term, path, factset, preds=False):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        for segment in path[:-1]:
            term = term.get_object(segment)
        return term

    @classmethod
    def filter_segment_first_var(cls, qfacts, value, path, factset, taken_vars, sec_vars):
        salias = aliased(cls)
        talias = aliased(Term)
        if value.name in taken_vars:
            sec_vars.append({'cls': cls, 'path': path, 'first': taken_vars[value.name][1]})
            return qfacts
        else:
            taken_vars[value.name] = (path, salias)
        if value.bases:
            sbases = factset.lexicon.get_subterms(get_bases(value)[0])
        else:
            sbases = factset.lexicon.get_subterms(value.term_type)
        sbases = [b.id for b in sbases]
        path_str = '.'.join(path)
        qfacts = qfacts.join(salias, Fact.id==salias.fact_id).filter(salias.path==path_str).join(talias, salias.term_id==talias.id).filter(talias.type_id.in_(sbases))
        return qfacts

    @classmethod
    def filter_segment_sec_var(cls, qfacts, path, salias):
        alias = aliased(cls)
        path_str = '.'.join(path)
        qfacts = qfacts.join(alias, Fact.id==alias.fact_id).filter(alias.path==path_str, alias.term_id==salias.term_id)
        return qfacts


class VerbSegment(Segment):

    __mapper_args__ = {'polymorphic_identity': '_verb'}
    verb_id = Column(Integer, ForeignKey('terms.id'), index=True)
    value = relationship('Term',
                         primaryjoin="Term.id==VerbSegment.verb_id")
    
    @classmethod
    def resolve(cls, term, path, factset, preds=False):
        for segment in path[:-1]:
            term = term.get_object(segment)
        if term.var or preds:
            return term
        return term.term_type

    @classmethod
    def filter_segment_first_var(cls, qfacts, value, path, factset, taken_vars, sec_vars):
        salias = aliased(cls)
        talias = aliased(Term)
        if value.name in taken_vars:
            sec_vars.append({'cls': cls, 'path': path, 'first': taken_vars[value.name][1]})
            return qfacts
        else:
            taken_vars[value.name] = (path, salias)
#        if value.name == 'Exists1':
#            import pdb;pdb.set_trace()
        if isa(value, factset.lexicon.verb):
            sbases = factset.lexicon.get_subterms(get_bases(value)[0])
        elif isa(value, factset.lexicon.exists):
            sbases = factset.lexicon.get_subterms(value.term_type)
        sbases = [b.id for b in sbases]
        path_str = '.'.join(path)
        qfacts = qfacts.join(salias, Fact.id==salias.fact_id).filter(salias.path==path_str).join(talias, salias.verb_id==talias.id).filter(talias.id.in_(sbases))
        return qfacts

    @classmethod
    def filter_segment_sec_var(cls, qfacts, path, salias):
        alias = aliased(cls)
        path_str = '.'.join(path)
        qfacts = qfacts.join(alias, Fact.id==alias.fact_id).filter(alias.path==path_str, alias.verb_id==salias.verb_id)
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
