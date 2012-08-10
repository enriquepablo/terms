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

from terms import patterns
from terms.terms import get_bases
from terms.terms import Base, Term, ObjectType
from terms.terms import word, verb, noun, exists, thing, isa, are
from terms.utils import Match, merge_submatches

'''
En el match hay que poner words.
en un query hay que ir construyendola en match.fact, con cada new_match,
y sus valores estan dentro de match.fact.
en las reglas tienen ya el fact de entrada,
y se van cogiendo los valores de ese fact.
cuando se llega a un mnetwork,
las piezas del fact que haya que guardar se pasan a consecuences.

'''


class FactSet(object):
    """
    """

    def __init__(self, lexicon):
        self.session = lexicon.session
        self.lexicon = lexicon
        try:
            self.root = self.session.query(RootFNode).one()
        except OperationalError:
            self.root = None

    def initialize(self, commit=False):
        self.root = RootFNode()
        self.session.add(self.root)
        if commit:
            self.session.commit()

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
        try:
            return mapper.base_mapper.polymorphic_map[ntype].class_
        except KeyError:
            return None

    def add_fact(self, fact, _commit=True):
        paths = self.get_paths(fact)
        old_node = self.root
        for path in paths:
            node = self.get_or_create_node(old_node, fact, path)
            old_node = node
        if not old_node.terminal:
            fnode = Fact(fact)
            self.session.add(fnode)
            old_node.terminal = fnode
        if _commit:
            self.session.commit()

    def get_or_create_node(self, parent, term, path, _commit=False):
        ntype_name = path[-1]
        cls = self._get_nclass(ntype_name)
        value = cls.resolve(term, path, self)
        try:
            return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value).one()
        except NoResultFound:
            pass
        #  build the node and append it
        node = cls(value)
        self.session.add(node)
        parent.children.append(node)
        if not parent.child_path:
            parent.child_path = path
        if _commit:
            self.session.commit()
        return node


    def query(self, *q):
        '''
        q is a word or set of words,
        possibly with varnames
        '''
        submatches = []
        if not q:
            return submatches
        for w in q:
            m = Match(word, query=w)
            m.paths = self.get_paths(w)
            smatches = []
            ntype_name = self.root.child_path[-1]
            cls = self._get_nclass(ntype_name)
            cls.dispatch(self.root, m, smatches, self)
            submatches.append(smatches)
        return merge_submatches(submatches)


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
            for child in children:
                if isinstance(child, LabelFNode):
                    path = path[:-2] + (child.value, path[-1])
                    if path in match.paths:
                        match.paths.remove(path)
                new_match = match.copy()
                val = 
                m = patterns.varpat.match(name)
                if isa(value, word) and m:
                    if name not in match:
                        if m.group(2):
                            new_match[name] = child.value.term_type
                        else:
                            new_match[name] = child.value
                cls.dispatch(child, new_match, matches, factset)
        if parent.terminal:
            if not match.paths:
                match.fact = parent.terminal.fact
                matches.append(match)

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
        except AttributeError:
            return None
        return term.true

    @classmethod
    def get_children(cls, parent, match, value, factset):
        return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)


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
        except AttributeError:
            return None
        return term

    @classmethod
    def get_children(cls, parent, match, value, factset):
        if patterns.varpat.match(value.name):
            if name in match:
                return parent.children.filter(cls.value==value)
            else:
                if are(get_type(value), word):
                    sbases = factset.lexicon.get_subterms(factset.lexicon.get_bases(value)[0])
                else:
                    sbases = (value.term_type,) + factset.lexicon.get_subwords(value.term_type)
                return parent.children.join(cls, FactNode.id==cls.fnid).join(Term, cls.term_id==Term.id).filter(Term.type_id.in_(sbases))
        else:
            return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)


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
        if m:
            if value.name in match:
                value = match[value.name]
                return parent.children.filter(cls.value==value)
            else:
                if isa(value, verb):
                    sbases = factset.lexicon.get_subterms(factset.lexicon.get_bases(value)[0])
                elif isa(value, exists):
                    if m.group(2):
                        verb_ = factset.lexicon.get_bases(value)[0]
                        sbases = factset.lexicon.get_subterms(verb_)
                    else:
                        sbases = factset.lexicon.get_subterms(value.term_type)
                return parent.children.join(cls, FactNode.id==cls.fnid).join(Term, cls.term_id==Term.id).filter(Term.id.in_(sbases))
        else:
            return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)


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
    fact = relationship('Predicate', primaryjoin="Predicate.id==Fact.pred_id")

    def __init__(self, fact):
        self.fact = fact
