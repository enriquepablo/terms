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
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError

from terms.core import patterns, exceptions
from terms.core.terms import get_bases
from terms.core.terms import Base, Term, Predicate
from terms.core.terms import isa, are
from terms.core.utils import Match, merge_submatches


class FactSet(object):
    """
    """

    def __init__(self, lexicon, config):
        self.config = config
        self.session = lexicon.session
        self.lexicon = lexicon
        try:
            self.root = self.session.query(RootFNode).one()
        except NoResultFound:
            self.initialize()

    def initialize(self):
        self.root = RootFNode()
        self.session.add(self.root)

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
        exists = self.lexicon.get_term('exists')
        word = self.lexicon.get_term('word')
        for ob in sorted(pred.objects, key=lambda x: x.label):
            o = ob.value
            paths.append(path + (ob.label, '_label'))
            if isa(o, exists):
                self._recurse_paths(o, paths, path + (ob.label,))
            elif isa(o, word):
                paths.append(path + (ob.label, '_term'))
            else:
                pass
                # segment = get_type(o)  # XXX __isa__
                # paths.append(path + (ob.label, segment))

    def _get_nclass(self, ntype):
        mapper = FactNode.__mapper__
        return mapper.base_mapper.polymorphic_map[ntype].class_

    def add_fact(self, fact, _commit=False):
        paths = self.get_paths(fact)
        old_node = self.root
        for path in paths:
            old_node = self.get_or_create_node(old_node, fact, path)
        if not old_node.terminal:
            fnode = Fact(fact)
            old_node.terminal = fnode
        if _commit:
            self.session.commit()
        return old_node.terminal

    def del_fact(self, match):
        FactNode.dispatch_rm(self.root, match, self)

    def get_or_create_node(self, parent, term, path):
        ntype_name = path[-1]
        cls = self._get_nclass(ntype_name)
        value = cls.resolve(term, path, self)
        try:
            node = parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value).one()
        except NoResultFound:
            #  build the node and append it
            node = cls(value)
            self.session.add(node)
            parent.children.append(node)
            if not parent.child_path:
                parent.child_path = path
#        if cls is VerbFNode:
#            pred = TermFNode.resolve(term, path, self)
#            node.preds.append(pred)
        return node


    def query(self, *q):
        '''
        q is a word or set of words,
        possibly with varnames
        '''
        word = self.lexicon.get_term('word')
        submatches = []
        if not q or not self.root.child_path:
            return submatches
        for w in q:
            m = Match(word, query=w)
            m.paths = self.get_paths(w)
            smatches = []
            FactNode.dispatch(self.root, m, smatches, self)
            submatches.append(smatches)
        return merge_submatches(submatches)

    def facts_from_node(self, node):
        facts = []
        self._recurse_facts_from_node(node, node, facts)
        return facts

    def _recurse_facts_from_node(self, prim, node, facts):
        if self.terminal:
            facts.append(self.terminal.fact)
        if len(node.child_path) >= len(prim.child_path):
            for ch in self.children:
                self._recurse_facts_from_node(prim, ch, facts)


class FactNode(Base):
    '''
    An abstact node in the network of facts.
    It is extended by concrete node classes.
    '''
    __tablename__ = 'factnodes'

    id = Column(Integer, Sequence('factnode_id_seq'), primary_key=True)
    child_path_str = Column(String)
    parent_id = Column(Integer, ForeignKey('factnodes.id'))
    children = relationship('FactNode',
                         backref=backref('parent',
                                         uselist=False,
                                         cascade='all',
                                         remote_side=[id]),
                         primaryjoin="FactNode.id==FactNode.parent_id",
                         lazy='dynamic')

    ntype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': ntype}

    def _get_path(self):
        try:
            return self._path
        except AttributeError:
            try:
                self._path = tuple(self.child_path_str.split('.'))
            except AttributeError:
                return ()
        return self._path

    def _set_path(self, path):
        self.child_path_str = '.'.join(path)
        self._path = path

    child_path = property(_get_path, _set_path)

    @classmethod
    def dispatch(cls, parent, match, matches, factset):
        if parent.child_path:
            path = parent.child_path
            if path in match.paths:
                match.paths.remove(path)
            ntype_name = path[-1]
            cls = factset._get_nclass(ntype_name)
            value = cls.resolve(match.query, path, factset)
            name = getattr(value, 'name', '')
            if value is None:
                children = parent.children.all()
            else:
                children = cls.get_children(parent, match, value, factset)
            exists = factset.lexicon.get_term('exists')
            for child in children:
                if isinstance(child, LabelFNode):
                    path = path[:-2] + (child.value, path[-1])
                    if path in match.paths:
                        match.paths.remove(path)
                new_match = match.copy()
                m = patterns.varpat.match(name)
                if m:
                    if name not in match:
                        if isa(value, exists):
                            new_match[name] = Predicate(True, child.value)
                            new_match.building = new_match[name]
                            new_match.orig_path = path
                        else:
                            new_match[name] = child.value
                elif new_match.building:
                    child.update_pred(new_match, path)
                cls.dispatch(child, new_match, matches, factset)
        if parent.terminal:
            if not match.paths:
                match.paths = factset.get_paths(match.fact)
                match.fnode = parent.terminal
                match.fact = parent.terminal.fact
                matches.append(match)

    @classmethod
    def dispatch_rm(cls, parent, match, factset):
        if parent.child_path:
            path = parent.child_path
            if path in match.paths:
                match.paths.remove(path)
            ntype_name = path[-1]
            cls = factset._get_nclass(ntype_name)
            value = cls.resolve(match.fact, path, factset)
            if value is None:
                children = parent.children.all()
            else:
                children = cls.get_children(parent, match, value, factset)
            exists = factset.lexicon.get_term('exists')
            for child in children:
                if isinstance(child, LabelFNode):
                    path = path[:-2] + (child.value, path[-1])
                    if path in match.paths:
                        match.paths.remove(path)
                new_match = match.copy()
                cls.dispatch_rm(child, new_match, factset)
        if parent.terminal:
            for a in parent.terminal.ancestors:
                if not len(a.parents) == 1 or not a.parents[0].id == parent.terminal.id:
                    raise exceptions.Contradiction('Cannot retract ' + str(parent.terminal.fact))
            if not match.paths:
                parent.terminal.rm_descent(factset)
                factset.session.delete(parent.terminal)


    @classmethod
    def resolve(cls, w, path, factset):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        raise NotImplementedError

    @classmethod
    def get_children(cls, parent, match, value, factset):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        raise NotImplementedError

    def update_pred(self, match, path):
        '''
        When a Exists var has previously matched,
        update its match with the value of self
        '''
        pass


class RootFNode(FactNode):
    '''
    A root factnode
    '''
    __tablename__ = 'rootfnodes'
    __mapper_args__ = {'polymorphic_identity': '_root'}
    fnid = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)


class NegFNode(FactNode):
    '''
    A node that tests whether a predicate is negated
    '''
    __tablename__ = 'negfnodes'
    __mapper_args__ = {'polymorphic_identity': '_neg'}
    fnid = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)

    value = Column(Boolean)

    def __init__(self, true):
        self.value = true
    
    @classmethod
    def resolve(cls, term, path, factset):
        try:
            for segment in path[:-1]:
                term = term.get_object(segment)
            return term.true
        except AttributeError:
            return None

    @classmethod
    def get_children(cls, parent, match, value, factset):
        return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)

    def update_pred(self, match, path):
        olen = len(match.orig_path)
        if olen > len(path):
            match.orig_path = ()
            match.building = None
            return None
        rel_path = path[olen - 1:]
        obj = match.building
        for segment in rel_path[:-1]:
            obj = obj.get_object(segment)
        obj.true = self.value

class TermFNode(FactNode):
    '''
    '''
    __tablename__ = 'termfnodes'
    __mapper_args__ = {'polymorphic_identity': '_term'}
    fnid = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term',
                         primaryjoin="Term.id==TermFNode.term_id")

    def __init__(self, term):
        self.value = term
    
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
    def get_children(cls, parent, match, value, factset):
        word = factset.lexicon.get_term('word')
        if patterns.varpat.match(value.name):
            if value.name in match:
                return parent.children.filter(cls.value==value)
            else:
                if value.bases:
                    sbases = factset.lexicon.get_subterms(get_bases(value)[0])
                else:
                    sbases = (value.term_type,) + factset.lexicon.get_subterms(value.term_type)
                sbases = (b.id for b in sbases)
                if sbases:
                    return parent.children.join(cls, FactNode.id==cls.fnid).join(Term, cls.term_id==Term.id).filter(Term.type_id.in_(sbases))
                return ()
        else:
            return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)

    def update_pred(self, match, path):
        olen = len(match.orig_path)
        if olen >= len(path):
            match.orig_path = ()
            match.building = None
            return None
        rel_path = path[olen - 1:]
        obj = match.building
        for segment in rel_path[:-2]:
            obj = obj.get_object(segment)
        obj.add_object(self.parent.value, self.value)


class VerbFNode(FactNode):
    '''
    '''
    __tablename__ = 'verbfnodes'
    __mapper_args__ = {'polymorphic_identity': '_verb'}
    fnid = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term',
                         primaryjoin="Term.id==VerbFNode.term_id")

    def __init__(self, term):
        self.value = term
    
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
    def get_children(cls, parent, match, value, factset):
        m = patterns.varpat.match(value.name)
        verb = factset.lexicon.get_term('verb')
        exists = factset.lexicon.get_term('exists')
        if m:
            if value.name in match:
                value = match[value.name]
                return parent.children.filter(cls.value==value)
            else:
                if isa(value, verb):
                    sbases = factset.lexicon.get_subterms(get_bases(value)[0])
                elif isa(value, exists):
                    sbases = factset.lexicon.get_subterms(value.term_type)
                sbases = (b.id for b in sbases)
                if sbases:
                    return parent.children.join(cls, FactNode.id==cls.fnid).join(Term, cls.term_id==Term.id).filter(Term.id.in_(sbases))
                return ()
        else:
            return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)

    def update_pred(self, match, path):
        olen = len(match.orig_path)
        if olen >= len(path):
            match.orig_path = ()
            match.building = None
            return None
        rel_path = path[olen - 1:]
        obj = match.building
        for segment in rel_path[:-2]:
            obj = obj.get_object(segment)
        pred = Predicate(True, self.value)
        obj.add_object(self.parent.value, pred)


class LabelFNode(FactNode):
    '''
    '''
    __tablename__ = 'labelfnodes'
    __mapper_args__ = {'polymorphic_identity': '_label'}
    fnid = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)
    value = Column(String)

    def __init__(self, label):
        self.value = label
    
    @classmethod
    def resolve(cls, term, path, factset):
        return path[-2]

    @classmethod
    def get_children(cls, parent, match, value, factset):
        return parent.children.all()


class Fact(Base):
    '''
    a terminal node for a fact
    '''
    __tablename__ = 'facts'

    id = Column(Integer, Sequence('fact_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('factnodes.id'))
    parent = relationship('FactNode', backref=backref('terminal', uselist=False),
                         primaryjoin="FactNode.id==Fact.parent_id")
    pred_id = Column(Integer, ForeignKey('predicates.id'))
    fact = relationship('Predicate', backref=backref('facts'),
                         cascade='all',
                         primaryjoin="Predicate.id==Fact.pred_id")

    def __init__(self, fact):
        self.fact = fact
        self.ancestors = []

    def rm_descent(self, factset):
        for d in self.descent:
            for ch in d.children:
                for a in ch.ancestors:
                    if len(a.parents) == 1 and a.parents[0].id == ch.id:
                        break
                else:
                    ch.rm_descent(factset)
                    factset.session.delete(ch)

ancestor_child = Table('ancestor_child', Base.metadata,
    Column('ancestor_id', Integer, ForeignKey('ancestors.id')),
    Column('child_id', Integer, ForeignKey('facts.id'))
)

ancestor_parent = Table('ancestor_parent', Base.metadata,
    Column('ancestor_id', Integer, ForeignKey('ancestors.id')),
    Column('parent_id', Integer, ForeignKey('facts.id'))
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
