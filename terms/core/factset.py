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

import operator

from sqlalchemy import Table, Column, Sequence
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy import sql

from terms.core.terms import get_bases
from terms.core.terms import Base, Term
from terms.core.terms import isa
from terms.core.utils import Match

from logging import getLogger
logger = getLogger(__name__)


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
        if not isa(pred, self.lexicon.verb):  # not a verb var
            paths.append(path + ('_neg',))
        for label in sorted(pred.objects):
            o = pred.objects[label].value
            if isa(o, self.lexicon.exist):
                self._recurse_paths(o, paths, path + (label,))
            elif isa(o, self.lexicon.number):
                paths.append(path + (label, '_num'))
            else:
                paths.append(path + (label, '_term'))

    def _get_nclass(self, path):
        ntype = path[-1]
        mapper = Segment.__mapper__
        return mapper.base_mapper.polymorphic_map[ntype].class_

    def add_fact(self, pred):
        logger.info('Adding {!r} to factset {}'.format(pred, self.name))
        fact = Fact(pred, self.name)
        paths = self.get_paths(pred)
        for path in paths:
            cls = self._get_nclass(path)
            value = cls.resolve(pred, path, self)
            cls(fact, value, path)
        self.session.add(fact)
        self.session.flush()
        return fact

    def add_object_to_fact(self, fact, value, path):
        cls = self._get_nclass(path)
        segment = cls(fact, value, path)
        self.session.add(segment)
        fact.pred.add_object(path[-2], value)

    def query_facts(self, pred, taken_vars, with_factset=True):
        vars = []
        sec_vars = []
        paths = self.get_paths(pred)
        qfacts = self.session.query(Fact)
        if with_factset:
            qfacts = qfacts.filter(Fact.factset==self.name)
        for path in paths:
            cls = self._get_nclass(path)
            value = cls.resolve(pred, path, self)
            if value is not None:
                qfacts = cls.filter_segment(qfacts, value, vars, path)
        vars.sort(key=lambda x: 1 if getattr(x, 'set_condition', False) else 0)
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
    def filter_segment_sec_var(cls, qfacts, path, salias):
        alias = aliased(cls)
        path_str = '.'.join(path)
        qfacts = qfacts.join(alias, Fact.id==alias.fact_id).filter(alias.path==path_str, alias.term_id==salias.term_id)
        return qfacts


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
    def filter_segment_first_var(cls, qfacts, value, path, factset, taken_vars, sec_vars):
        salias = aliased(cls)
        talias = aliased(Term)
        if value.name in taken_vars:
            sec_vars.append({'cls': cls, 'path': path, 'first': taken_vars[value.name][1]})
            return qfacts
        else:
            taken_vars[value.name] = (path, salias)
        path_str = '.'.join(path)
        if value.bases:
            sbases = [b.id for b in factset.lexicon.get_subterms(value.bases[0])]
            qfacts = qfacts.join(salias, Fact.id==salias.fact_id).filter(salias.path==path_str).join(talias, salias.term_id==talias.id).filter(talias.id.in_(sbases))
        else:
            sbases = [b.id for b in factset.lexicon.get_subterms(value.term_type)]
            qfacts = qfacts.join(salias, Fact.id==salias.fact_id).filter(salias.path==path_str).join(talias, salias.term_id==talias.id).filter(talias.type_id.in_(sbases))
        return qfacts


class NumberSegment(Segment):

    __mapper_args__ = {'polymorphic_identity': '_num'}
    int_value = Column(Integer, index=True)

    binopers = {
        '|': sql.or_,
        '&': sql.and_,
        '=': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '%': operator.mod,
    }
    unopers = {
        '~': sql.not_,
        '-': operator.neg,
    }

    def __init__(self, fact, value, path):
        self.fact = fact
        if getattr(value, 'name', False):
            value = int(value.name)
        self.value = value
        self.path = '.'.join(path)

    @property
    def value(self):
        return self.int_value

    @value.setter
    def value(self, val):
        self.int_value = val

    @classmethod
    def filter_segment(cls, qfact, value, vars, path):
        if getattr(value, 'var', False):
            vars.append({'cls': cls, 'value': value, 'path': path})
        else:
            alias = aliased(cls)
            path_str = '.'.join(path)
            qfact = qfact.join(alias, Fact.id==alias.fact_id).filter(alias.int_value==int(value.name), alias.path==path_str)
        return qfact

    @classmethod
    def filter_segment_first_var(cls, qfacts, value, path, factset, taken_vars, sec_vars):
        alias = aliased(cls)
        taken_vars[value.name] = (path, alias)
        path_str = '.'.join(path)
        qfacts = qfacts.join(alias, Fact.id==alias.fact_id).filter(alias.path==path_str)
        if getattr(value, 'set_condition', False):
            condition = cls.compile_condition(value.set_condition, taken_vars)
            qfacts = qfacts.filter(condition)
        return qfacts

    @classmethod
    def compile_condition(cls, expr, taken_vars):
        if expr.type == 's-vnum':
            return cls.compile_vnum(expr, taken_vars)
        oper = expr.oper
        arg1 = cls.compile_condition(expr.arg1, taken_vars)
        if expr.arg2 is not None:
            arg2 = cls.compile_condition(expr.arg2, taken_vars)
            return cls.binopers[oper](arg1, arg2)
        return cls.unopers[oper](arg1)

    @classmethod
    def compile_vnum(cls, vnum, taken_vars):
        if vnum.var:
            alias = taken_vars[vnum.val][1]
            return getattr(alias, 'int_value')
        return int(vnum.val)


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
        elif isa(value, factset.lexicon.exist):
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
