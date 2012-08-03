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
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from terms import patterns
from terms.terms import Base, Session, Term
from terms.words import word, verb, noun, exists, thing, isa, are
from terms.words import get_name, get_type, get_bases, negate
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
        except NoResultFound:
            self.root = RootFNode()
            self.session.add(self.root)
            self.session.commit()

    def get_paths(self, w):
        '''
        build a path for each testable feature in w (a word).
        Each path is a tuple of strings,
        and corresponds to a node in the primary network.
        '''
        paths = []
        self._recurse_paths(w, paths, ())
        return paths

    def _recurse_paths(self, pred, paths, path):
        paths.append(path + ('_verb',))
        paths.append(path + ('_neg',))
        for l in sorted(pred.objs):
            if not hasattr(pred, l):
                continue
            o = getattr(pred, l)
            paths.append(path + (l, '_label'))
            if isa(o, exists):
                self._recurse_paths(o, paths, path + (l,))
            elif isa(o, word):
                paths.append(path + (l, '_term'))
            else:
                segment = get_type(o)  # XXX __isa__
                paths.append(path + (l, segment))

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
            fnode = Fact()
            self.session.add(fnode)
            old_node.terminal = fnode
            self.session.commit()

    def get_or_create_node(self, parent, w, path):
        ntype_name = path[-1]
        cls = self._get_nclass(ntype_name)
        wvalue = cls.resolve(w, path, self)
        value = cls.get_qval(wvalue, self)
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
        self.session.commit()
        return node


    @classmethod
    def make_pred(cls, verb_, **objs):
        name = get_name(verb_)
        obj_list = sorted(objs.items(), key=lambda x: x[0])
        for label, obj in obj_list:
            name += '__' + label + '__' + get_name(obj)
        return verb_(name, (), objs)


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
                return False
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
            children = cls.get_children(parent, match, value, factset)
            for child in children:
                if isinstance(child, LabelFNode):
                    path = path[:-2] + (child.value, path[-1])
                    if path in match.paths:
                        match.paths.remove(path)
                new_match = match.copy()
                wval = child.update_match(new_match, path, factset)
                if isa(value, word) and patterns.varpat.match(get_name(value)):
                    name = get_name(value)
                    if name not in match:
                        new_match[name] = wval
                cls.dispatch(child, new_match, matches, factset)
        if parent.terminal:
            if not match.paths:
                matches.append(match)

    def update_match(self, match, path, factset):
        # get current pred (from match.fact/path)
        # get value from self
        pass

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

    @classmethod
    def get_qval(cls, value, factset):
        '''
        From a word value, get a value
        ready for use in a db query
        '''
        return value


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
    def resolve(cls, w, path, factset):
        try:
            for segment in path[:-1]:
                w = getattr(w, segment)
        except AttributeError:
            return None
        return w.true

    @classmethod
    def get_children(cls, parent, match, value, factset):
        if value is None:
            return parent.children.all()
        return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)

    def update_match(self, match, path, factset):
        pred = match.fact
        for segment in path[:-1]:
            pred = getattr(pred, segment)
        negate(pred)


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
    def resolve(cls, w, path, factset):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        try:
            for segment in path[:-1]:
                w = getattr(w, segment)
        except AttributeError:
            return None
        return w

    @classmethod
    def get_children(cls, parent, match, value, factset):
        if value is None:
            return parent.children.all()
        name = get_name(value)
        if patterns.varpat.match(name):
            if name in match:
                value = factset.lexicon.get_term(get_name(match[name]))
                return parent.children.filter(cls.value==value)
            else:
                if isa(value, noun) or isa(value, verb) or get_type(value) is word:
                    sbases = factset.lexicon.get_subwords(get_bases(value)[0])
                else:
                    sbases = (get_type(value),) + factset.lexicon.get_subwords(get_type(value))
                stypes = [factset.lexicon.get_term(get_name(b)).id for b in sbases]
                return parent.children.join(cls, FactNode.id==cls.fnid).join(Term, cls.term_id==Term.id).filter(Term.type_id.in_(stypes))
        else:
            value = factset.lexicon.get_term(name)
            return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)

    def update_match(self, match, path, factset):
        pred = match.fact
        for segment in path[:-2]:
            pred = getattr(pred, segment)
        w = factset.lexicon.get_word(self.value.name)
        setattr(pred, path[-2], w)
        return w

    @classmethod
    def get_qval(cls, value, factset):
        return factset.lexicon.get_term(get_name(value))


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
    def resolve(cls, w, path, factset):
        try:
            for segment in path[:-1]:
                w = getattr(w, segment)
        except AttributeError:
            return None
        return get_type(w)

    @classmethod
    def get_children(cls, parent, match, value, factset):
        if value is None:
            return parent.children.all()
        name = get_name(value)
        if patterns.varpat.match(name):
            if name in match:
                value = factset.lexicon.get_term(get_name(match[name]))
                return parent.children.filter(cls.value==value)
            else:
                if isa(value, verb):
                    sbases = factset.lexicon.get_subwords(get_bases(value)[0])
                elif isa(value, exists):
                    sbases = (get_type(value),) + factset.lexicon.get_subwords(get_type(value))
                stypes = [factset.lexicon.get_term(get_name(b)).id for b in sbases]
                return parent.children.join(cls, FactNode.id==cls.fnid).join(Term, cls.term_id==Term.id).filter(Term.id.in_(stypes))
        else:
            value = factset.lexicon.get_term(name)
            return parent.children.join(cls, FactNode.id==cls.fnid).filter(cls.value==value)

    def update_match(self, match, path, factset):
        verb_ = factset.lexicon.get_word(self.value.name)
        npred = factset.make_pred(verb_)
        if len(path) > 1:
            pred = match.fact
            for segment in path[:-2]:
                pred = getattr(pred, segment)
            setattr(pred, path[-2], npred)
        else:
            match.fact = npred
        return npred

    @classmethod
    def get_qval(cls, value, factset):
        return factset.lexicon.get_term(get_name(value))


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
    def resolve(cls, w, path, factset):
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
