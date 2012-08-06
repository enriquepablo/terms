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
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError

from terms.terms import Base, Term
from terms.predicates import Predicate
from terms.lexicon import Lexicon
from terms.factset import FactSet
from terms.utils import Match
from terms.patterns import varpat
    

class Network(object):

    def __init__(self, dbaddr='sqlite:///:memory:'):
        self.engine = create_engine(dbaddr)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.lexicon = Lexicon(self.session)
        self.factset = FactSet(self.lexicon)
        try:
            self.root = self.session.query(RootNode).one()
        except OperationalError:
            self.initialize()

    def initialize(self):
        Base.metadata.create_all(self.engine)
        self.lexicon.initialize()
        self.factset.initialize()
        self.root = RootNode()
        self.session.commit()

    def _get_nclass(self, ntype):
        mapper = Node.__mapper__
        try:
            return mapper.base_mapper.polymorphic_map[ntype].class_
        except KeyError:
            return None

    def add_fact(self, fact):
        m = Match(fact)
        m.paths = self.factset.get_paths(w)
        ntype_name = self.root.child_path[-1]
        cls = self._get_nclass(ntype_name)
        cls.dispatch(self.root, m, fact, self)
        self.factset.add_fact(fact)

    def add_rule(self, wprems, conds, wcons, orders=None, _commit=True):
        rule = Rule(self)
        for wprem in wprems:
            var_map = []
            paths = self.factset.get_paths(wprem)
            old_node = self.root
            for path in paths:
                node = self.get_or_create_node(old_node, fact, path, var_map)
                old_node = node
            pnode = PremNode()
            old_node.terminals.append(pnode)
            pnode.children.append(rule)
            for varname, num in var_map.items():
                rule.pvars.append(PVarname(pnode, num, varname))
        rule.conds = conds
        for wcon in wcons:
            rule.cons.append(Consecuence(wcon))
        if _commit:
            self.session.commit()

    def get_or_create_node(self, parent, w, path, var_map, _commit=False):
        ntype_name = path[-1]
        cls = self._get_nclass(ntype_name)
        wvalue = cls.resolve(w, path, self)
        name = get_name(wvalue)
        value = cls.get_qval(wvalue, self)
        try:
            return parent.children.join(cls, Node.id==cls.nid).filter(cls.value==value).one()
        except NoResultFound:
            #  build the node and append it
            node = cls(value)
            self.session.add(node)
            parent.children.append(node)
            if not parent.child_path:
                parent.child_path = path
            if _commit:
                self.session.commit()
            return node


class Node(Base):
    '''
    An abstact node in the primary (or premises) network.
    It is extended by concrete node classes.
    '''
    __tablename__ = 'nodes'
    id = Column(Integer, Sequence('node_id_seq'), primary_key=True)
    child_path_str = Column(String)
    var = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey('nodes.id'))
    children = relationship('Node',
                         backref=backref('parent',
                                         uselist=False,
                                         remote_side=[id]),
                         primaryjoin="Node.id==Node.parent_id",
                         lazy='dynamic')

    ntype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': ntype}


    def __init__(self, var=0):
        self.var = var  # int
        # self.children = []  # nodes
        # self.terminals = []  # prem nodes (terminals)

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
        self.child_path_str = path[-1]
        self._path = path

    child_path = property(_get_path, _set_path)

    @classmethod
    def resolve(cls, w, path):
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

    @classmethod
    def dispatch(cls, parent, match, value, network):
        if self.var:
            if self.var not in match:
                match[self.var] = value
        if parent.child_path:
            path = parent.child_path
            ntype_name = path[-1]
            cls = network._get_nclass(ntype_name)
            value = cls.resolve(match.fact, path)
            name = get_name(value)
            children = cls.get_children(parent, match, value, network)
            for child in children:
                new_match = match.copy()
                cls.dispatch(child, new_match, value, network)
        for t in parent.terminals:
            new_match = match.copy()
            t.dispatch(new_match)

    @classmethod
    def get_children(cls, parent, match, value, factset):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        raise NotImplementedError

    def filter_children(self, match):
        if not self.children:
            return []
        value = self.resolve(match.fact, self.child_path)
        vals = self.children[0].get_values(value, match)
        #  XXX query = not self.var and self.value.in_(vals) or self.var in match and self.value.in_(match[self.var]) or match[self.var] = self.value and isa(vals[0], self.value)
        return self.filter(Node.var==self.var, self.__class__.value.in_(vals))


class RootNode(Node):
    '''
    A root node
    '''
    __tablename__ = 'rootnodes'
    __mapper_args__ = {'polymorphic_identity': '_root'}
    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)


class NegNode(Node):
    '''
    A node that tests whether a predicate is negated
    '''
    __tablename__ = 'negnodes'
    __mapper_args__ = {'polymorphic_identity': '_neg'}

    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)
    value = Column(Boolean)

    def __init__(self, true, *args, **kwargs):
        self.value = true
        super(NegNode, self).__init__(*args, **kwargs)
    
    @classmethod
    def resolve(cls, w, path):
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
        return parent.children.join(cls, Node.id==cls.nid).filter(cls.value==value)


class TermNode(Node):
    '''
    '''
    __tablename__ = 'termnodes'
    __mapper_args__ = {'polymorphic_identity': '_term'}
    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term',
                         primaryjoin="Term.id==TermNode.term_id")

    def __init__(self, term, *args, **kwargs):
        self.value = term
        super(TermNode, self).__init__(*args, **kwargs)
    
    @classmethod
    def resolve(cls, w, path):
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
    def get_qval(cls, value, network):
        name = get_name(value)
        m = patterns.varpat.match(name)
        if m:
            name = ''.join(m.groups())
        try:
            qval = network.lexicon.get_term(get_name(value))
        except exceptions.TermNotFound:
            if m:
                return network.lexicon.save_var(value)
            else:
                raise


    @classmethod
    def get_children(cls, parent, match, value, network):
        if value is None:
            return parent.children.all()
        qval = cls.get_qval(value, network)
        children = parent.children.join(cls, Node.id==cls.fnid).filter(cls.value==qval)
        for k, v in match.items():
            if v == prev
                vchildren = parent.children.filter(Node.var==k)
                break
        else:
            types = (get_type(value),) + get_bases(get_type(value))
            type_ids = [factset.lexicon.get_term(get_name(t)).id for t in types]
            vchildren = parent.children.join(cls, Node.id==cls.nid).join(Term, cls.term_id==Term.id).filter(Term.var>0).filter(Term.parent_id.in_(type_ids))
            bases = factset.lexicon.get_subwords(get_bases(value)[0])
            if bases:
                tbases = aliased(Term)
                base_ids = [factset.lexicon.get_term(get_name(b)).id for b in bases]
                vchildren = vchildren.join(terms_to_bases, Term.id==terms_to_bases.child_id).join(tbases, terms_to_bases.base_id==tbases.id).filter(tbases.id.in_(base_ids))
        return children, vchildren


class VerbNode(Node):
    '''
    '''
    __tablename__ = 'verbnodes'
    __mapper_args__ = {'polymorphic_identity': '_verb'}
    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term',
                         primaryjoin="Term.id==VerbNode.term_id")

    def __init__(self, term):
        self.value = term
    
    @classmethod
    def resolve(cls, w, path):
        try:
            for segment in path[:-1]:
                w = getattr(w, segment)
        except AttributeError:
            return None
        if patterns.varpat.match(get_name(w)):
            return w
        return get_type(w)

    @classmethod
    def get_qval(cls, value, network):
        name = get_name(value)
        m = patterns.varpat.match(name)
        if m:
            name = ''.join(m.groups())
        try:
            qval = network.lexicon.get_term(get_name(value))
        except exceptions.TermNotFound:
            if m:
                return network.lexicon.save_var(value)
            else:
                raise

    @classmethod
    def get_children(cls, parent, match, value, network):
        if value is None:
            return parent.children.all()
        qval = cls.get_qval(value, network)
        children = parent.children.join(cls, Node.id==cls.fnid).filter(cls.value==qval)
        for k, v in match.items():
            if v == prev
                vchildren = parent.children.filter(Node.var==k) # XXX falta poner las var
                break
        else:
            types = (get_type(value),) + get_bases(get_type(value))
            type_ids = [factset.lexicon.get_term(get_name(t)).id for t in types]
            chvars = parent.children.join(cls, Node.id==cls.nid).join(Term, cls.term_id==Term.id).filter(Term.var>0)
            pchildren = chvars.filter(Term.parent_id.in_(type_ids))
            tbases = aliased(Term)
            vchildren = chvars.join(terms_to_bases, Term.id==terms_to_bases.child_id).join(tbases, terms_to_bases.base_id==tbases.id).filter(tbases.id.in_(base_ids))
        return children, pchildren, vchildren


class LabelNode(Node):
    '''
    '''
    __tablename__ = 'labelnodes'
    __mapper_args__ = {'polymorphic_identity': '_label'}
    id = Column(Integer, ForeignKey('nodes.id'), primary_key=True)
    value = Column(String)

    def __init__(self, label, *args, **kwargs):
        self.value = label
        super(LabelNode, self).__init__(*args, **kwargs)

    @classmethod
    def resolve(cls, w, path):
        return path[-2]

    @classmethod
    def get_children(cls, parent, match, value, factset):
        return parent.children.all()


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
    __tablename__ = 'strconobjects'
    __mapper_args__ = {'polymorphic_identity': 0}
    id = Column(Integer, ForeignKey('conobjects.id'), primary_key=True)
    value = Column(String)


class SenConObject(ConObject):
    '''
    '''
    __tablename__ = 'senconobjects'
    __mapper_args__ = {'polymorphic_identity': 1}
    id = Column(Integer, ForeignKey('conobjects.id'), primary_key=True)
    con_id = Column(Integer, ForeignKey('consecuences.id'))
    value = relationship('Consecuence',
                         primaryjoin="Consecuence.id==SenConObject.con_id")
