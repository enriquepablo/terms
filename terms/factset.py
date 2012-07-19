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
from sqlalchemy.orm import relationship

from terms.terms import Base
from terms.words import get_name, get_type


def get_paths(w):
    '''
    build a path for each testable feature in w (a word).
    Each path is a tuple of strings,
    and corresponds to a node in the primary network.
    '''
    paths = []
    _recurse_paths(w, paths, ())
    return paths

def _recurse_paths(pred, paths, path):
    paths.append(path + ('_neg',))
    paths.append(path + ('_verb',))
    for l, o in pred.args:
        paths.append(path + (l, '_label'))
        if isa(o, exists):
            _recurse_paths(o, paths, path + (l,))
        elif isa(o, word):
            paths.append(path + (l, '_term'))
        else:
            segment = get_type(o)  # XXX __isa__
            paths.append(path + (l, segment))

def resolve(w, path):
    '''
    Get the value pointed at by path in w (a word).
    It can be a boolean (for neg nodes),
    a sting (for label nodes),
    a word, or some custom value for custom node types.
    '''
    for segment in path:
        if segment == '_neg':
            return w.true
        elif segment == '_verb':
            return get_term(get_type(w))
        elif segment == '_label':
            return path[-2]
        elif segment == '_term':
            return get_term(w)
        else:
            nclass = Node._get_nclass(segment)
            if nclass:
                return nclass._get_val(w, path)
            else:
                w = getattr(w, segment)
    return w

class Match(dict):

    def __init__(self, fact, *args, **kwargs):
        self.fact = fact  # word
        self.prem = None
        super(Match, self).__init__(*args, **kwargs)

    def copy(self):
        new_match = Match(self.fact)
        for k, v in self.items():
            new_match[k] = v
        new_match.prem = self.prem
        return new_match


class FactSet(object):
    """
    """

    def __init__(self, lexicon):
        self.session = lexicon.session
        self.lexicon = lexicon
        self.root = RootFNode()

    @classmethod
    def _get_nclass(self, ntype):
        mapper = Node.__mapper__
        try:
            return mapper.base_mapper.polymorphic_map[ntype_name].class_
        except KeyError:
            return None

    @classmethod
    def _get_val(self, w, path):
        raise NotImplementedError

    def add_fact(self, fact, _commit=True):
        paths = get_paths(fact)
        old_node = self.root
        for path in paths:
            ntype_name = path[-1]
            nclass = self._get_nclass(ntype_name)
            node = nclass.get_or_create(old_node, fact, path)
            old_node = node
        if not old_node.terminal:
            fnode = Fact()
            old_node.terminal = fnode


    @classmethod
    def make_pred(cls, verb_, **objs):
        name = get_name(verb_)
        obj_list = list(objs.items())
        obj_list = sorted(obj_list, key=lambda x: x[0])
        for label, obj in obj_list:
            name += '__' + label + '__' + get_name(obj)
        return verb_(name, (), objs)


    def query(self, q):
        pass




class FactNode(Base):
    '''
    An abstact node in the network of facts.
    It is extended by concrete node classes.
    '''
    __tablename__ = 'factnodes'

    id = Column(Integer, Sequence('factnode_id_seq'), primary_key=True)
    child_path_str = Column(String)
    parent_id = Column(Integer, ForeignKey('factnodes.id'))
    parent = relationship('FactNode', remote_side=[id], backref='children',
                         primaryjoin="FactNode.id==FactNode.parent_id")

    ntype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': ntype}


    def _get_path(self):
        try:
            return self._path
        except AttributeError:
            try:
                self._path = self.parent.child_path + tuple(self.child_path_str)
            except AttributeError:
                self._path = tuple(self.child_path_str)
            return self._path

    def _set_path(self, path):
        self.child_path_str = path[-1]
        self._path = path

    child_path = property(_get_path, _set_path)

    @classmethod
    def get_or_create(cls, parent, w, path):
        value = resolve(w, path)
        try:
            return parent.children.filter(cls.value==value).one()
        except NoResultFound:
            pass
        #  build the node and append it
        node = cls(value)
        parent.children.append(node)
        if not parent.child_path:
            parent.child_path = path
        return node


class RootFNode(FactNode):
    '''
    A root factnode
    '''
    __tablename__ = 'rootfnodes'
    __mapper_args__ = {'polymorphic_identity': '_root'}
    id = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)


class NegFNode(FactNode):
    '''
    A node that tests whether a predicate is negated
    '''
    __tablename__ = 'negfnodes'
    __mapper_args__ = {'polymorphic_identity': '_neg'}
    id = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)

    value = Column(Boolean)

    def __init__(self, true):
        self.value = true


class TermFNode(FactNode):
    '''
    '''
    __tablename__ = 'termfnodes'
    __mapper_args__ = {'polymorphic_identity': '_term'}
    id = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term',
                         primaryjoin="Term.id==TermFNode.term_id")

    def __init__(self, term):
        self.value = term


class LabelFNode(FactNode):
    '''
    '''
    __tablename__ = 'labelfnodes'
    __mapper_args__ = {'polymorphic_identity': '_label'}
    id = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)
    value = Column(String)

    def __init__(self, label):
        self.value = label
