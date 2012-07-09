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

from sqlalchemy import Table, Column, Sequence
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from terms.terms import Base, Term
from terms.predicates import Predicates

node_types = []

node_type_names = {}


def register(tname):
    '''
    class decorator generator,
    used for Node classes.

    Takes a string (tname),
    and when a class is created,
    registers the name and the class
    so they can later be retrieved through
    get_tnode() and get_tnum().

    Also sets the provided tname
    as a class attribute (tname) on the class.
    '''
    def fun(nodeclass):
        n = len(node_types)
        node_type_names[tname] = n
        node_types.append(nodeclass)
        nodeclass.tname = tname
        return nodeclass
    return fun

def get_tnode(tname):
    '''
    if a class has been registered with tname,
    this returns the class.

    Otherwise returns None
    '''
    if isinstance(tname, int):
        return node_types[tname]
    else:
        return node_types[node_type_names[tname]]

def get_tnum(tname):
    '''
    Given a string tname,
    if it has been used to register a class,
    returns the order in which it was registered.
    
    Otherwise raises KeyError
    '''
    return node_type_names[tname]

def get_ntype(w):
    '''
    Get the registration name of the node class
    that corresponds to the provided word w.
    '''
    if isinstance(w, boolean):
        return '_neg'
    elif isinstance(w, str):
        return '_label'
    elif isinstance(w, thing):
        return '_elem'
    elif isinstance(w, exists):
        return '_pred'
    elif isinstance(w, word):
        return '_set'
    else:
        return get_name(w)

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
    paths.append(path + ('neg',))
    paths.append(path + ('verb',))
    for l, o in pred.args:
        paths.append(path + (l, 'label'))
        if isinstance(o, exists):
            _recurse_paths(o, paths, path + (l,))
        else:
            paths.append(path + (l,))

def resolve(w, path):
    '''
    Get the value pointed at by path in w (a word).
    It can be a boolean (for neg nodes),
    a sting (for label nodes),
    a word, or some custom value for custom node types.
    '''
    for segment in path:
        if segment in special_resolvers:
            w = special_resolvers[segment](w, path)
        else:
            w = getattr(obj, segment, None)
    return w

special_resolvers = {}

def _res_neg(o, path):
    return o.true

special_resolvers['_neg'] = _res_neg


def _res_verb(o, path):
    return get_type(o)

special_resolvers['_verb'] = _res_verb


def _res_label(o, path):
    return path[-2]

special_resolvers['_label'] = _res_label


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


class Node(Base):
    '''
    An abstact node in the primary (or premises) network.
    It is extended by concrete node classes.
    '''
    __tablename__ = 'nodes'

    id = Column(Integer, Sequence('term_id_seq'), primary_key=True)
    path_str = Column(String)
    var = Column(Integer)
    parent_id = Column(Integer, ForeignKey('nodes.id'))
    parent = relationship('Node', remote_side=[id], backref='children',
                         primaryjoin="Node.id==Node.parent_id")

    ntype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': ntype}


    def __init__(self, network, path, var=0):
        self.path = path  # tuple
        self.var = var  # int
        self.ntype = get_tnum(self.tname)  #  node type num
        # self.children = []  # nodes
        # self.terminals = []  # prem nodes (terminals)

    def _get_path(self):
        try:
            return self._path
        except AttributeError:
            self._path = tuple(self.path_str.split('.'))
            return self._path

    def _set_path(self, path):
        self.path_str = '.'.join(path)
        self._path = path

    path = property(_get_path, _set_path)

    def filter_siblings(self, parent, match):
        raise NotImplementedError

    def dispatch(self, match):
        if self.var:
            if self.var in match:
                if match[self.var] != self.get_val():
                    return
            else:
                match[self.var] = self.get_val()
        if self.children:
            children = self.children[0].filter_siblings(self, match)
            for child in children:
                new_match = match.copy()
                child.dispatch(new_match)
        if self.terminals:
            for p in self.terminals:
                new_match = match.copy()
                p.dispatch(new_match)

    def get_val(self):
        raise NotImplementedError

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        raise NotImplementedError


@register('_neg')
class NegNode(Node):
    '''
    A node that tests whether a predicate is negated
    '''
    __mapper_args__ = {'polymorphic_identity': get_tnum(self.tname)}
    id = Column(Integer, ForeignKey('Node.id'), primary_key=True)

    true = Column(Boolean)

    def __init__(self, true, *args, **kwargs):
        self.true = true
        super(NegNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        true = resolve(match.fact, self.path)
        if true == self.true:
            return (self,)
        return (parent.children[1],)

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        try:
            return parent.children.filter(NegNode.true==w).one()
        except NotFound:
            pass
        #  build the node and append it
        node = NegNode(true, path, t=get_type_num(cls.tname))
        parent.children.append(node)
        return node


@register('_set')
class SetNode(TermNode):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': get_tnum(self.tname)}
    id = Column(Integer, ForeignKey('Node.id'), primary_key=True)
    term = Column(Integer, ForeignKey('Term.id'))

    def __init__(self, term, *args, **kwargs):
        self.term = term
        super(SetNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        w = resolve(match.fact, self.path)
        words = lexicon.get_subwords(w)
        terms = [lexicon.get_term(w) for w in words]
        return parent.children.filter(SetNode.var==w.var, SetNode.term.in_(terms))

    def get_val(self):
        return self.term

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        term = lexicon.get_term(w)
        m = p.VAR_PAT.match(get_name(w))
        if m:
            if name in var_map:
                var = var_map[name]
            else:
                var_map.count += 1
                var = var_map[name] = var_map.count
        else:
            var = 0
        try:
            return parent.children.filter(SetNode.term==term, SetNode.var==var).one()
        except NotFound:
            pass
        #  build the node and append it
        node = SetNode(term, path, var=var, t=get_type_num(cls.tname))
        parent.children.append(node)
        return node

@register('_elem')
class NameNode(TermNode):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': get_tnum(self.tname)}
    id = Column(Integer, ForeignKey('Node.id'), primary_key=True)
    term = Column(Integer, ForeignKey('Term.id'))

    def __init__(self, term, *args, **kwargs):
        self.term = term
        super(NameNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        w = resolve(match.fact, self.path)
        return parent.children.filter(NameNode.term == lexicon.get_term(w),
                                      NameNode.var == w.var)

    def get_val(self):
        return self.term

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        '''
        Used when adding premises to the network.

        Getting the child nodes of a node depends
        on the node type of the children.
        We use this class method to get
        a child of parent,
        were parent is a node of any class
        and its children nodes of this class.
        '''
        term = lexicon.get_term(w)
        name = get_name(w)
        m = p.VAR_PAT.match(name)
        if m:
            if name in var_map:
                var = var_map[name]
            else:
                var_map.count += 1
                var = var_map[name] = var_map.count
        else:
            var = 0
        try:
            return parent.children.filter(NameNode.term == term,
                                          NameNode.var == var).one()
        except NotFound:
            pass
        #  build the node and append it
        node = NameNode(term, path, var=var, t=get_type_num(cls.tname))
        parent.children.append(node)
        return node


@register('_label')
class LabelNode(TermNode):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': get_tnum(self.tname)}
    id = Column(Integer, ForeignKey('Node.id'), primary_key=True)
    label = Column(String)

    def __init__(self, label, *args, **kwargs):
        self.label = label
        super(LabelNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        w = resolve(match.fact, self.path)
        sibs = []
        for sib in parent.children:
            if hasattr(w, sib.label):
                sibs.append(sib)
        return sibs

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        try:
            return parent.children.filter(LabelNode.label == w).one()
        except NotFound:
            pass
        #  build the node and append it
        node = LabelNode(w, path, t=get_tnum(cls.tname))
        parent.children.append(node)
        return node


prem_to_rule = Table('prem_to_rule', Base.metadata,
    Column('prem_id', Integer, ForeignKey('prems.id'), primary_key=True),
    Column('rule_id', Integer, ForeignKey('rules.id'), primary_key=True)
)


class PremNode(Base):
    '''
    a terminal node for a premise
    '''
    id = Column(Integer, Sequence('term_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('nodes.id'))
    parent = relationship('Node', backref='terminals',
                         primaryjoin="Node.id==PremNode.parent_id")
    rules = relationship('RuleNode', backref='prems',
                         secondary=prem_to_rule,
                         primaryjoin=id==prem_to_rule.c.prem_id,
                         secondaryjoin=id==prem_to_rule.c.rule_id)

    def __init__(self, parent):
        self.parent = parent  # node
        self.rules = []  # rules

    def dispatch(self, match):
        match.prem = self
        for child in self.rules:
            new_match = match.copy()
            child.dispatch(new_match)


class MNodeDispatcher(object):

    def dispatch_to_children(self, match, old_matches):

        if old_matches is None:
            old_matches = []

        new_matches = []
        first = self.children.first()
        var = first.var
        if var in match:
            matching = self.filter_value(match[var])
        else:
            matching = False

        if not matching: 
            new_match = match.copy()
            new_match[self.var] = self.value
            if len(new_match) == len(self.rule.vrs):
                return [new_match]
            else:
                old_matches_c = old_matches[:]
                old_matches_c.append(self.var)
                self.add_mnodes(new_match, old_matches_c)
                return []  # XXX

        for child in matching:
            new_matches.append(child.dispatch(match, old_matches))
        return [m for matches in new_matches for m in matches]

    def _add_mnodes(self, match, old_matches, rule, hint=None):
        if not hint:
            left = filter(lambda x: x not in old_matches, match.keys())
            if not left:
                return
            hint = left[0]
        mnode = MNode(hint, match[hint], rule)
        self.children.append(mnode)
        old_matches.append(hint)
        mnode.add_mnodes(match, old_matches)

    def filter_value(self, val):
        raise NotImplementedError


class Varname(object):
    """
    a variable in a rule,
    it has a name
    """
    def __init__(self, name, rule):
        self.name = name
        self.rule = rule


class MNode(object, MNodeDispatcher):

    def __init__(self, var, value, rule):
        self.var = var  # varname
        self.value = value  # term
        self.rule = rule  # rule
        self.chidren = []  # mnodes
        self.parents = []  # facts that have supported it

    def dispatch(self, match, old_matches=None):
        """
        returns
         * None : mismatch
         * [] : no matches
         * [m1, m2...] : matches
        """
        return self.dispatch_to_children(match, old_matches)

    def add_mnodes(self, match, old_matches, hint=None):
        self._add_mnodes(match, old_matches, self.rule, hint=hint)

    def filter_value(self, val):
        bases = lexicon.get_bases(val)
        return self.children.filter(MNode.value.in_(bases))



class PVarname(object):
    """
    Mapping from varnames in rules (pvars belong in rules)
    to premise, number.
    Premises have numbered variables;
    and different rules can share a premise,
    but translate differently its numbrered vars to varnames.
    """

    def __init__(self, prem, num, name):
        self.prem = prem
        self.num = num
        self.name = name


class Arg(object):

    def __init__(self, val):
        if isinstance(val, Term):
            self.term = val
        else:
            self.var = val

    def resolve(self, match):
        if self.var:
            return match.substitutions[self.var]
        return self.term


class Condition(object):

    def __init__(self, fpath, *args):
        self.fun = fresolve(fpath)  # callable
        self.fpath = fpath  # string
        self.args = args  # Arg. terms have conversors for different funs

    def test(self, match):
        sargs = []
        for arg in args:
            sargs.append(arg.resolve(match))
        return self.fun(*sargs)


class Rule(TermNode, MNodeDispatcher):

    def __init__(self, network):
        self.network = network
        self.prems = []  # pred nodes
        self.pvars = []  # pvars
        self.vrs = []  # string
        self.children = []  # mnodes
        self.conditions = []  # conditions
        self.cons = []  # consecuences
        self.rule = self  # for dispatch_to_children

    def dispatch(self, match):
        new_match = Match(match.sen)
        for num, o in match.subs.items():
            pvar = self.pvars.filter(prem=match.prem, num=num).one()
            varname = pvar.name
            new_match.subs[varname] = o
        old_matches = []
        if not self.children:
            if len(new_match.subs) == len(self.rule.vrs):
                matches = [new_match]
            else:
                self.add_mnodes(new_match, old_matches)
                matches = []
        else:
            matches = self.dispatch_to_children(new_match, old_matches)

        new = []
        for m in matches:
            for cond in self.conditions:
                if not cond.test(m):
                    break
            else:
                new.append(m)

        kb = self.network.kb
        for m in matches:
            for con in self.cons:
                kb.factset.add_fact(con.substitute(m))
        return new or False
    
    def filter_siblings(self, parent, match):
        return parent.children

    def add_mnodes(self, match):
        self._add_mnodes(match, [], self)


class Network(object):

    def __init__(self, kb):
        self.kb = kb

    def add_fact(self, fact):
        m = Match(fact)
        if self.children:
            children = self.children[0].filter_siblings(self, m)
            for ch in children:
                ch.dispatch(m)
        self.kb.factset.add_fact(fact)

    def add_rule(self, wprems, conds, wcons, orders=None):
        rule = Rule(self)
        for wprem in wprems:
            var_map = []
            paths = get_paths(wprem)
            old_node = self
            for path in paths:
                w = resolve(prem, path)
                ntype = get_ntype(w)
                nclass = get_tnode(ntype)
                node = nclass.get_node(old_node, w, path, var_map)
                old_node = node
            pnode = PremNode()
            old_node.terminals.append(pnode)
            pnode.children.append(rule)
            for varname, num in var_map.items():
                rule.pvars.append(PVarname(pnode, num, varname))
        rule.conds = conds
        for wcon in wcons:
            rule.cons.append(Consecuence(wcon))


class Consecuence(object):
    '''
    Consecuences in rules.
    '''
    def __init__(self, wpred):
        '''
        verb is a string.
        args is a dict with strings (labels) to ConObjects
        '''
        self.true = true  # boolean
        self.verb = verb  # string
        self.args = []  # StringObjects
        for k, v in args.items():
            self.args.append(ConObject(k, v))


class StringObject(object):
    '''
    objects for StringSentences
    '''
    def __init__(self, label, obj):
        self.label = label  # string
        self.ty = 'string'  # string/sentence to discriminate among StringStrObject/StringSenObject


class StringStrObject(StringObject):
    # discriminated on self.ty
    def __init__(self, label, obj):
        self.label = label  # string
        self.ty = 'string'
        self.obj = obj  # string


class StringSenObject(StringObject):
    # discriminated on self.ty
    def __init__(self, label, obj):
        self.label = label  # string
        self.ty = 'sentence'
        self.obj = obj  # StringSentence
