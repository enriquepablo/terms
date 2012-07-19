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

from terms.terms import Base, Session
from terms.words import word, verb, noun, exists, thing, isa, are
from terms.words import get_name, get_type


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

    def merge(self, m):
        new_match = Match(self.fact)
        for k, v in self.items() + m.items():
            if k in m:
                if self[k] != v:
                    return False
            new_match[k] = v
        return new_match


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
        paths.append(path + ('_neg',))
        paths.append(path + ('_verb',))
        for l in sorted(pred.objs):
            o = pred.objs[l]
            paths.append(path + (l, '_label'))
            if isa(o, exists):
                self._recurse_paths(o, paths, path + (l,))
            elif isa(o, word):
                paths.append(path + (l, '_term'))
            else:
                segment = get_type(o)  # XXX __isa__
                paths.append(path + (l, segment))

    def resolve(self, cls, w, path):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        for segment in path[:-1]:
            w = getattr(w, segment)
        name = get_name(w)
        if patterns.varpat.match(name):
            return w
        return cls.get_qval(w, path, self.lexicon)

    def _get_nclass(self, ntype):
        mapper = FactNode.__mapper__
        try:
            return mapper.base_mapper.polymorphic_map[ntype].class_
        except KeyError:
            return None

    @classmethod
    def _get_val(self, w, path):
        raise NotImplementedError

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
        value = self.resolve(cls, w, path)
        try:
            return parent.children.filter(cls.value==value).one()
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
        obj_list = list(objs.items())
        obj_list = sorted(obj_list, key=lambda x: x[0])
        for label, obj in obj_list:
            name += '__' + label + '__' + get_name(obj)
        return verb_(name, (), objs)


    def query(self, *q):
        '''
        q is a word or set of words,
        possibly with varnames
        '''
        submatches = []
        for w in q:
            pmatches = self.root.dispatch(w)
            submatches.append(pmatches)
        return self.merge(submatches)

    def merge(self, submatches):
        final = []
        while submatches:
            sm = submatches.pop()
            new = []
            for m in final:
                for n in sm:
                    nm = m.merge(n)
                    if nm:
                        new.append(nm)
            final = new
        return final

    def dispatch(self, parent, match, lexicon, matches):
        ntype_name = parent.child_path[-1]
        cls = self._get_nclass(ntype_name)
        value = self.resolve(cls, match.fact, parent.child_path)
        isvar = False
        if isa(value, word):  # var        XXX Aquí voy añadiendo queries a factset, después hay que pasar el trabajo de factset a network
            isvar = True
            name = get_name(value)
            if name in match:
                children = parent.children.filter(cls.value==match[name])
            else:
                stypes = self.lexicon.get_subterms(lexicon.get_term(get_name(get_type(value))))
                children = parent.children.filter(cls.parent.in_(stypes))
        else:
            children = parent.children.filter(cls.value==value)
        for child in children:
            new_match = match.copy()
            if isvar and name not in match:
                new_match[name] = child
            self.dispatch(child, new_match, lexicon, matches)
        if self.terminal:
            matches.append(match)


class FactNode(Base):
    '''
    An abstact node in the network of facts.
    It is extended by concrete node classes.
    '''
    __tablename__ = 'factnodes'

    id = Column(Integer, Sequence('factnode_id_seq'), primary_key=True)
    child_path_str = Column(String)
    parent_id = Column(Integer, ForeignKey('factnodes.id'))
    parent = relationship('FactNode',
                         backref=backref('children', remote_side=[id], lazy='dynamic'),
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
                try:
                    self._path = tuple(self.child_path_str)
                except TypeError:
                    return False
            return self._path

    def _set_path(self, path):
        self.child_path_str = path[-1]
        self._path = path

    child_path = property(_get_path, _set_path)

    @classmethod
    def get_qval(cls, w, path):
        raise NotImplementedError



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
    
    @classmethod
    def get_qval(cls, w, path, lexicon):
        return w.true


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

    @classmethod
    def get_qval(cls, w, path, lexicon):
        return lexicon.get_term(get_name(w))


class VerbFNode(FactNode):
    '''
    '''
    __tablename__ = 'verbfnodes'
    __mapper_args__ = {'polymorphic_identity': '_verb'}
    id = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term',
                         primaryjoin="Term.id==VerbFNode.term_id")

    def __init__(self, term):
        self.value = term

    @classmethod
    def get_qval(cls, w, path, lexicon):
        return lexicon.get_term(get_name(get_type(w)))


class LabelFNode(FactNode):
    '''
    '''
    __tablename__ = 'labelfnodes'
    __mapper_args__ = {'polymorphic_identity': '_label'}
    id = Column(Integer, ForeignKey('factnodes.id'), primary_key=True)
    value = Column(String)

    def __init__(self, label):
        self.value = label

    @classmethod
    def get_qval(cls, w, path, lexicon):
        return path[-2]


class Fact(Base):
    '''
    a terminal node for a fact
    '''
    __tablename__ = 'facts'

    id = Column(Integer, Sequence('fact_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('factnodes.id'))
    parent = relationship('FactNode', backref=backref('terminal', uselist=False),
                         primaryjoin="FactNode.id==Fact.parent_id")
