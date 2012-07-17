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
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from terms.terms import Base, Term
from terms.predicates import Predicate
from terms.lexicon import Lexicon
from terms.factset import FactSet

node_types = []

node_type_names = {}


# XXX this registry should be persistent
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
        node_types.append(nodeclass)
        nodeclass.tname = tname
        return nodeclass
    return fun

def reg_tnum(tname):
    n = len(node_types)
    node_type_names[tname] = n
    return n

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
    that corresponds to the provided word w,
    as returned by resolve.
    '''
    if isinstance(w, boolean):
        return '_neg'
    elif isinstance(w, str):
        return '_label'
    elif isa(w, thing):
        return '_elem'
    elif isa(w, exists):
        return '_pred'
    elif are(w, word):
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
        if isa(o, exists):
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
            w = getattr(w, segment, None)
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

    id = Column(Integer, Sequence('node_id_seq'), primary_key=True)
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


@register('_root')
class RootNode(Node):
    '''
    A root node
    '''
    __mapper_args__ = {'polymorphic_identity': reg_tnum('_root')}

    def __init__(self, *args, **kwargs):
        super(RootNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        return (self,)

    def get_node(self, parent, w, var_map):
        return (self,)


@register('_neg')
class NegNode(Node):
    '''
    A node that tests whether a predicate is negated
    '''
    __mapper_args__ = {'polymorphic_identity': reg_tnum('_neg')}

    true = Column(Boolean)

    def __init__(self, true, *args, **kwargs):
        self.true = true
        super(NegNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        true = resolve(match.fact, self.path)
        if true == self.true:
            return (self,)
        return (parent.children[1],)

    def get_node(self, parent, w, var_map):
        try:
            return parent.children.filter(NegNode.true==w).one()
        except NoResultFound:
            pass
        #  build the node and append it
        node = NegNode(true, self.path, t=get_type_num(NegNode.tname))
        parent.children.append(node)
        return node


@register('_term')
class TermNode(Node):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': reg_tnum('_term')}
    term_id = Column(Integer, ForeignKey('terms.id'))
    term = relationship('Term',
                         primaryjoin="Term.id==TermNode.term_id")

    def __init__(self, term, *args, **kwargs):
        self.term = term
        super(TermNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        w = resolve(match.fact, self.path)
        words = lexicon.get_subwords(w)
        terms = [lexicon.get_term(w) for w in words]
        return parent.children.filter(SetNode.var==w.var, SetNode.term.in_(terms))

    def get_val(self):
        return self.term

    def get_node(self, parent, w, var_map):
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
        except NoResultFound:
            pass
        #  build the node and append it
        node = SetNode(term, self.path, var=var, t=get_type_num(SetNode.tname))
        parent.children.append(node)
        return node


@register('_label')
class LabelNode(TermNode):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': reg_tnum('_label')}
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

    def get_node(self, parent, w, var_map):
        try:
            return parent.children.filter(LabelNode.label == w).one()
        except NoResultFound:
            pass
        #  build the node and append it
        node = LabelNode(w, self.path, t=get_tnum(LabelNode.tname))
        parent.children.append(node)
        return node


prem_to_rule = Table('prem_to_rule', Base.metadata,
    Column('prem_id', Integer, ForeignKey('premnodes.id'), primary_key=True),
    Column('rule_id', Integer, ForeignKey('rules.id'), primary_key=True)
)


class PremNode(Base):
    '''
    a terminal node for a premise
    '''
    __tablename__ = 'premnodes'

    id = Column(Integer, Sequence('premnode_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('nodes.id'))
    parent = relationship('Node', backref='terminals',
                         primaryjoin="Node.id==PremNode.parent_id")
    rules = relationship('Rule', backref='prems',
                         secondary=prem_to_rule,
                         foreign_keys=[prem_to_rule.c.prem_id, prem_to_rule.c.rule_id],
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


class Varname(Base):
    """
    a variable in a rule,
    it has a name
    """
    __tablename__ = 'varnames'

    id = Column(Integer, Sequence('varname_id_seq'), primary_key=True)
    name = Column(String)
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref='varnames',
                         primaryjoin="Rule.id==Varname.rule_id")

    def __init__(self, name, rule):
        self.name = name
        self.rule = rule


class MNode(Base):
    '''
    '''
    __tablename__ = 'mnodes'


    id = Column(Integer, Sequence('mnode_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('mnodes.id'))
    parent = relationship('MNode', remote_side=[id], backref='children',
                         primaryjoin="MNode.id==MNode.parent_id")
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref='mnodes',
                         primaryjoin="Rule.id==MNode.rule_id")
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term', backref='mnodes',
                         primaryjoin="Term.id==MNode.term_id")
    varname_id = Column(Integer, ForeignKey('varnames.id'))
    var = relationship('Varname', backref='mnodes',
                         primaryjoin="Varname.id==MNode.varname_id")
    predicate_id = Column(Integer, ForeignKey('predicates.id'))
    support = relationship('Predicate', backref='mnodes',
                         primaryjoin="Predicate.id==MNode.predicate_id")

    def __init__(self, var, value, rule):
        self.var = var  # varname
        self.value = value  # term
        self.rule = rule
        # self.chidren = []  # mnodes
        # self.support = []  # facts that have supported it

    def dispatch(self, match, matched=None):
        """
        returns
         * None : mismatch
         * [] : no matches
         * [m1, m2...] : matches
        """

        if matched is None:
            matched = []

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
                new_matched = matched[:]
                new_matched.append(self.var)
                self.add_mnodes(new_match, new_matched)
                return []  # XXX

        for child in matching:
            new_matches.append(child.dispatch(match, matched))
        return [m for matches in new_matches for m in matches]

    def add_mnodes(self, match, matched, hint=None):
        if not hint:
            left = filter(lambda x: x not in matched, match.keys())
            if not left:
                return
            hint = left[0]
        mnode = MNode(hint, match[hint], self.rule)
        self.children.append(mnode)
        matched.append(hint)
        mnode.add_mnodes(match, matched)

    def filter_value(self, val):
        bases = lexicon.get_bases(val)
        return self.children.filter(MNode.value.in_(bases))



class PVarname(Base):
    """
    Mapping from varnames in rules (pvars belong in rules)
    to premise, number.
    Premises have numbered variables;
    and different rules can share a premise,
    but translate differently its numbrered vars to varnames.
    """
    __tablename__ = 'pvarnames'


    id = Column(Integer, Sequence('mnode_id_seq'), primary_key=True)
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref='pvars',
                         primaryjoin="Rule.id==PVarname.rule_id")
    prem_id = Column(Integer, ForeignKey('premnodes.id'))
    prem = relationship('PremNode', backref='pvars',
                         primaryjoin="PremNode.id==PVarname.prem_id")
    varname_id = Column(Integer, ForeignKey('varnames.id'))
    varname = relationship('Varname', backref='pvarnames',
                         primaryjoin="Varname.id==PVarname.varname_id")
    num = Column(Integer)

    def __init__(self, rule, prem, num, name):
        self.rule = rule
        self.prem = prem
        self.num = num
        self.varname = name


class CondArg(Base):
    '''
    '''
    __tablename__ = 'condargs'

    id = Column(Integer, Sequence('condarg_id_seq'), primary_key=True)
    cond_id = Column(Integer, ForeignKey('conditions.id'))
    cond = relationship('Condition', backref='args',
                         primaryjoin="Condition.id==CondArg.cond_id")
    varname_id = Column(Integer, ForeignKey('varnames.id'))
    varname = relationship('Varname', backref='condargs',
                         primaryjoin="Varname.id==CondArg.varname_id")
    term_id = Column(Integer, ForeignKey('terms.id'))
    term = relationship('Term',
                         primaryjoin="Term.id==CondArg.term_id")

    def __init__(self, val, ):
        if isinstance(val, Term):
            self.term = val
        elif isinstance(val, Varname):
            self.varname = val

    def solve(self, match):
        if self.var:
            return match[self.var.name]
        return self.term


class Condition(Base):
    '''
    '''
    __tablename__ = 'conditions'

    id = Column(Integer, Sequence('condition_id_seq'), primary_key=True)
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref='conditions',
                         primaryjoin="Rule.id==Condition.rule_id")
    fpath = Column(String)

    def __init__(self, rule, fpath, *args):
        self.rule = rule
        self.fun = fresolve(fpath)  # callable
        self.fpath = fpath  # string
        for arg in args:
            self.args.append(arg)  # Arg. terms have conversors for different funs

    def test(self, match):
        sargs = []
        for arg in args:
            sargs.append(arg.solve(match))
        return self.fun(*sargs)


class Rule(Base):
    '''
    '''
    __tablename__ = 'rules'

    id = Column(Integer, Sequence('rule_id_seq'), primary_key=True)

    def __init__(self, network):
        self.network = network
        self.prems = []  # pred nodes
        self.pvars = []  # pvars
        self.vrs = []  # string
        self.conditions = []  # conditions
        self.cons = []  # consecuences
        self.mroot = MNode(None, None, self)  # empty mnode

    def dispatch(self, match):
        new_match = Match(match.sen)
        for num, o in match.items():
            pvar = self.pvars.filter(prem=match.prem, num=num).one()
            varname = pvar.name
            new_match[varname] = o
        matched = []
        if not self.root.children:
            if len(new_match) == len(self.vrs):
                matches = [new_match]
            else:
                self.root.add_mnodes(new_match, matched)
                matches = []
        else:
            matches = self.root.dispatch(new_match, matched)

        new = []
        for m in matches:
            for cond in self.conditions:
                if not cond.test(m):
                    break
            else:
                new.append(m)

        kb = self.network.kb
        for m in new:
            for con in self.cons:
                kb.factset.add_fact(con.substitute(m))
        return new or False
    

class Network(object):

    def __init__(self, dbaddr='sqlite:///:memory:'):
        self.engine = create_engine(dbaddr)
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()
        try:
            self.root = self.session.query(RootNode).one()
        except:
            self.initialize()
        self.lexicon = Lexicon(self.session)
        self.factset = FactSet(self.lexicon)

    def initialize(self):
        Base.metadata.create_all(self.engine)
        self.root = RootNode(self, '')
        self.session.commit()

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


class Consecuence(Base):
    '''
    Consecuences in rules.
    '''
    __tablename__ = 'consecuences'

    id = Column(Integer, Sequence('consecuence_id_seq'), primary_key=True)
    true = Column(Boolean)
    verb = Column(String)

    ntype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': ntype}

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


class ConObject(Base):
    '''
    objects for StringSentences
    '''
    __tablename__ = 'conobjects'

    id = Column(Integer, Sequence('conobject_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('consecuences.id'))
    parent = relationship('Consecuence', backref='args',
                         primaryjoin="Consecuence.id==ConObject.parent_id")
    label = Column(String)

    cotype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': cotype}

    def __init__(self, parent, label, val):
        self.parent = parent
        self.label = label  # string
        self.value = val


class StrConObject(ConObject):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': 0}
    value = Column(String)


class SenConObject(ConObject):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': 1}
    con_id = Column(Integer, ForeignKey('consecuences.id'))
    value = relationship('Consecuence',
                         primaryjoin="Consecuence.id==SenConObject.con_id")
