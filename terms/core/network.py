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
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError

from terms.core.terms import isa, are, get_bases
from terms.core.terms import Base, Term, term_to_base, Predicate
from terms.core.lexicon import Lexicon
from terms.core.factset import FactSet, Ancestor
from terms.core import exceptions
from terms.core import patterns
from terms.core.utils import Match


class Network(object):

    def __init__(self, session, config):
        self.session = session
        self.config = config
        initialize = False
        try:
            self.root = self.session.query(RootNode).one()
        except OperationalError:
            initialize =  True
            self.initialize()
        self.lexicon = Lexicon(self.session, config)
        self.factset = FactSet(self.lexicon, config)
        if initialize:
            self.session.commit()

    def initialize(self):
        Base.metadata.create_all(self.session.connection().engine)
        self.root = RootNode()
        self.session.add(self.root)

    def _get_nclass(self, ntype):
        mapper = Node.__mapper__
        return mapper.base_mapper.polymorphic_map[ntype].class_

    def add_fact(self, fact, _commit=True):
        neg = fact.copy()
        neg.true = not neg.true
        contradiction = self.factset.query(neg)
        if contradiction:
            raise exceptions.Contradiction('we already have ' + str(neg))
        prev = self.factset.query(fact)
        fnode = self.factset.add_fact(fact)
        ancestor = Ancestor(fnode)
        ancestor.children.append(fnode)
        if prev:
            if _commit:
                self.session.commit()
            return
        if self.root.child_path:
            m = Match(fact)
            m.paths = self.factset.get_paths(fact)
            m.fnode = fnode
            Node.dispatch(self.root, m, self)
        if _commit:
            self.session.commit()
        return fnode

    def del_fact(self, fact, _commit=True):
        match = Match(fact)
        match.paths = self.factset.get_paths(fact)
        self.factset.del_fact(match)
        if _commit:
            self.session.commit()

    def add_rule(self, prems, conds, cons, orders=None, _commit=True):
        rule = Rule()
        prempairs = []
        for n, pred in enumerate(prems):
            vars = {}
            paths = self.factset.get_paths(pred)
            old_node = self.root
            for path in paths:
                node = self.get_or_create_node(old_node, pred, path, vars, rule)
                old_node = node
            if old_node.terminal:
                pnode = old_node.terminal
            else:
                pnode = PremNode(old_node)
                old_node.terminal = pnode
            premise = Premise(pnode, n, pred)
            rule.prems.append(premise)
            for n, varname in vars.values():
                rule.pvars.append(PVarname(premise, n, varname))
        rule.conditions = conds
        for con in cons:
            if isinstance(con, Predicate):
                rule.consecuences.append(con)
            else:
                rule.vconsecuences.append(con)
        for prem in rule.prems:
            matches = self.factset.query(prem.pred)
            for match in matches:
                prem.dispatch(match, self, _numvars=False)
        if _commit:
            self.session.commit()

    def get_or_create_node(self, parent, term, path, vars, rule):
        ntype_name = path[-1]
        cls = self._get_nclass(ntype_name)
        value = cls.resolve(term, path)
        name = getattr(value, 'name', '')
        m = patterns.varpat.match(name)
        pnum = 0
        if m:
            if name not in vars:
                pnum = len(vars) + 1
                vars[name] = (pnum, Varname(value, rule))
            else:
                pnum = vars[name][0]
        try:
            node = parent.children.join(cls, Node.id==cls.nid).filter(Node.var==pnum, cls.value==value).one()
        except NoResultFound:
            #  build the node and append it
            node = cls(value)
            node.var = pnum
            parent.children.append(node)
            if not parent.child_path:
                parent.child_path = path
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
                         cascade='all',
                         lazy='dynamic')

    ntype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': ntype}

    def __init__(self, value):
        self.value = value

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
    def resolve(cls, w, path):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        raise NotImplementedError

    @classmethod
    def dispatch(cls, parent, match, network):
        if parent.child_path:
            path = parent.child_path
            ntype_name = path[-1]
            chcls = network._get_nclass(ntype_name)
            value = chcls.resolve(match.fact, path)
            if value is None:
                children = [parent.children.all()]
            else:
                children = chcls.get_children(parent, match, value, network)
            for ch in children:
                for child in ch:
                    new_match = match.copy()
                    if child.var:
                        #if child.value.name == 'M7':
                        #    import pdb;pdb.set_trace()
                        if child.var not in match:
                            if chcls is VerbNode and isa(child.value, network.lexicon.exists):
                                new_match[child.var] = TermNode.resolve(match.fact, path)
                            elif value:
                                new_match[child.var] = value
                    chcls.dispatch(child, new_match, network)
        if parent.terminal:
            parent.terminal.dispatch(match, network)

    @classmethod
    def get_children(cls, parent, match, value, factset):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        raise NotImplementedError


class RootNode(Node):
    '''
    A root node
    '''
    __tablename__ = 'rootnodes'
    __mapper_args__ = {'polymorphic_identity': '_root'}
    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)

    def __init__(self):
        pass


class NegNode(Node):
    '''
    A node that tests whether a predicate is negated
    '''
    __tablename__ = 'negnodes'
    __mapper_args__ = {'polymorphic_identity': '_neg'}

    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)
    value = Column(Boolean)
    
    @classmethod
    def resolve(cls, term, path):
        try:
            for segment in path[:-1]:
                term = term.get_object(segment)
        except AttributeError:
            return None
        try:
            return term.true
        except AttributeError:
            # Predicate variable
            return True

    @classmethod
    def get_children(cls, parent, match, value, factset):
        return [parent.children.join(cls, Node.id==cls.nid).filter(cls.value==value)]


class TermNode(Node):
    '''
    '''
    __tablename__ = 'termnodes'
    __mapper_args__ = {'polymorphic_identity': '_term'}
    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term',
                         primaryjoin="Term.id==TermNode.term_id")
    
    @classmethod
    def resolve(cls, term, path):
        '''
        Get the value pointed at by path in w (a word).
        It can be a boolean (for neg nodes),
        a sting (for label nodes),
        a word, or some custom value for custom node types.
        '''
        try:
            for segment in path[:-1]:
                term = term.get_object(segment)
        except (AttributeError, KeyError):
            return None
        return term

    @classmethod
    def get_children(cls, parent, match, value, network):
        children = parent.children.join(cls, Node.id==cls.nid).filter(cls.value==value)
        vchildren = ()
        for k, v in match.items():
            if v == value:
                vchildren = parent.children.filter(Node.var==k)
                break
        else:
            types = (value.term_type,) + get_bases(value.term_type)
            type_ids = [t.id for t in types]
            if type_ids:
                vchildren = parent.children.join(cls, Node.id==cls.nid).join(Term, cls.term_id==Term.id).filter(Term.var==True).filter(Term.type_id.in_(type_ids))
            if not isa(value, network.lexicon.thing) and not isa(value, network.lexicon.number):
                bases = (value,) + get_bases(value)
                tbases = aliased(Term)
                base_ids = (b.id for b in bases)
                if base_ids and vchildren:
                    vchildren = vchildren.join(term_to_base, Term.id==term_to_base.c.term_id).join(tbases, term_to_base.c.base_id==tbases.id).filter(tbases.id.in_(base_ids))  # XXX can get duplicates
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
    
    @classmethod
    def resolve(cls, term, path):
        try:
            for segment in path[:-1]:
                term = term.get_object(segment)
        except (AttributeError, KeyError):
            return None
        if patterns.varpat.match(term.name):
            return term
        return term.term_type

    @classmethod
    def get_children(cls, parent, match, value, network):
        children = parent.children.join(cls, Node.id==cls.nid).filter(cls.value==value)
        pchildren = []
        for k,v in match.items():
            if v == value:
                vchildren = parent.children.filter(Node.var==k)
                break
        else:
            types = (value,) + get_bases(value)
            type_ids = [t.id for t in types]
            chvars = parent.children.filter(Node.var>0)
            pchildren = chvars.join(cls, Node.id==cls.nid).join(Term, cls.term_id==Term.id).filter(Term.type_id.in_(type_ids))
            tbases = aliased(Term)
            vchildren = chvars.join(cls, Node.id==cls.nid).join(Term, cls.term_id==Term.id).join(term_to_base, Term.id==term_to_base.c.term_id).join(tbases, term_to_base.c.base_id==tbases.id).filter(tbases.id.in_(type_ids))
        return children, pchildren, vchildren


class LabelNode(Node):
    '''
    '''
    __tablename__ = 'labelnodes'
    __mapper_args__ = {'polymorphic_identity': '_label'}
    nid = Column(Integer, ForeignKey('nodes.id'), primary_key=True)
    value = Column(String)

    @classmethod
    def resolve(cls, w, path):
        return path[-2]

    @classmethod
    def get_children(cls, parent, match, value, factset):
        return [parent.children.all()]


class Premise(Base):
    '''
    Relation between rules and premnodes
    '''
    __tablename__ = 'premises'

    id = Column(Integer, Sequence('premise_id_seq'), primary_key=True)
    prem_id = Column(Integer, ForeignKey('premnodes.id'))
    node = relationship('PremNode', backref='prems', 
                         primaryjoin="PremNode.id==Premise.prem_id")
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref=backref('prems', lazy='dynamic'),
                         primaryjoin="Rule.id==Premise.rule_id")
    pred_id = Column(Integer, ForeignKey('predicates.id'))
    pred = relationship('Predicate',
                         primaryjoin="Predicate.id==Premise.pred_id")
    order = Column(Integer)

    def __init__(self, pnode, order, pred):
        self.node = pnode
        self.order = order
        self.pred = pred

    def check_match(self, match, network):
        pred = self.pred
        prem_paths = network.factset.get_paths(pred)
        for p in prem_paths:
            if p not in match.paths:
                return False
        return True

    def dispatch(self, match, network, _numvars=True):
        rule = self.rule
        if _numvars:
            nmatch = match.copy()
            for num, o in match.items():
                pvar = self.pvars.filter(PVarname.rule==rule, PVarname.num==num).one()
                name = pvar.varname.name
                nmatch[name] = o
                del nmatch[num]
            matches = [nmatch]
        else:
            matches = [match]
        for prem in rule.prems:
            if not matches:
                break
            if prem.order == self.order:
                continue
            premnode = prem.node
            new_matches = []
            for m in matches:
                pvar_map = rule.get_pvar_map(m, prem)
                pmatches = premnode.matches
                for var, val in pvar_map:
                    apair = aliased(MPair)
                    if isinstance(val, Predicate):
                        cpair = aliased(PPair)
                    else:
                        cpair = aliased(TPair)
                    pmatches = pmatches.join(apair, PMatch.id==apair.parent_id).filter(apair.var==var)
                    pmatches = pmatches.join(cpair, apair.id==cpair.mid).filter(cpair.val==val)
                for pm in pmatches:
                    new_match = m.copy()
                    m.ancestor.parents.append(pm.fact)
                    for mpair in pm.pairs:
                        vname = rule.get_varname(prem, mpair.var)
                        if vname not in m:
                            new_match[vname] = mpair.val
                    new_matches.append(new_match)
            matches = new_matches
        for m in matches:
            rule.dispatch(m, network)



class PremNode(Base):
    '''
    a terminal node for a premise
    '''
    __tablename__ = 'premnodes'

    id = Column(Integer, Sequence('premnode_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('nodes.id'))
    parent = relationship('Node', backref=backref('terminal', uselist=False),
                         primaryjoin="Node.id==PremNode.parent_id")

    def __init__(self, parent):
        self.parent = parent  # node

    def dispatch(self, match, network, _numvars=True):
        if not self.prems[0].check_match(match, network):
            return
        m = PMatch(self, match.fnode)
        for var, val in match.items():
            m.pairs.append(MPair.make_pair(var, val))
        self.matches.append(m)
        match.ancestor = Ancestor(match.fnode)
        for premise in self.prems:
            premise.dispatch(match, network, _numvars=_numvars)


class PMatch(Base):
    __tablename__ = 'pmatchs'

    id = Column(Integer, Sequence('pmatch_id_seq'), primary_key=True)
    prem_id = Column(Integer, ForeignKey('premnodes.id'))
    prem = relationship('PremNode', backref=backref('matches', lazy='dynamic'),
                         primaryjoin="PremNode.id==PMatch.prem_id")
    fact_id = Column(Integer, ForeignKey('facts.id'))
    fact = relationship('Fact', backref=backref('matches', cascade='all'),
                         primaryjoin="Fact.id==PMatch.fact_id")

    def __init__(self, prem, fact):
        self.prem = prem
        self.fact = fact


class MPair(Base):
    __tablename__ = 'mpairs'

    id = Column(Integer, Sequence('mpair_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('pmatchs.id'))
    parent = relationship('PMatch', backref='pairs',
                         primaryjoin="PMatch.id==MPair.parent_id")
    var = Column(Integer)

    mtype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': mtype}

    def __init__(self, var, val):
        self.var = var
        self.val = val

    @classmethod
    def make_pair(cls, var, val):
        if isinstance(val, Predicate):
            return PPair(var, val)
        else:
            return TPair(var, val)

class TPair(MPair):
    __tablename__ = 'tpairs'
    __mapper_args__ = {'polymorphic_identity': 0}
    mid = Column(Integer, ForeignKey('mpairs.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    val = relationship('Term', primaryjoin="Term.id==TPair.term_id")


class PPair(MPair):
    __tablename__ = 'ppairs'
    __mapper_args__ = {'polymorphic_identity': 1}
    mid = Column(Integer, ForeignKey('mpairs.id'), primary_key=True)
    pred_id = Column(Integer, ForeignKey('predicates.id'))
    val = relationship('Predicate',
                         primaryjoin="Predicate.id==PPair.pred_id")

class Varname(Base):
    """
    a variable in a rule,
    it has a name
    """
    __tablename__ = 'varnames'

    id = Column(Integer, Sequence('varname_id_seq'), primary_key=True)
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref='varnames',
                         primaryjoin="Rule.id==Varname.rule_id")
    term_id = Column(Integer, ForeignKey('terms.id'))
    var = relationship('Term', backref='varnames',
                         primaryjoin="Term.id==Varname.term_id")

    def __init__(self, var, rule):
        self.var = var
        self.rule = rule

    def _get_name(self):
        return self.var.name

    name = property(_get_name)


class Rule(Base):
    '''
    '''
    __tablename__ = 'rules'

    id = Column(Integer, Sequence('rule_id_seq'), primary_key=True)

    def dispatch(self, match, network):

        for cond in self.conditions:
            if not cond.test(match, network):
                return
        cons = []
        for con in self.consecuences:
            cons.append(con.substitute(match))

        for con in self.vconsecuences:
            cons.append(match[con.name])

        for con in cons:
            prev = network.factset.query(con)
            fnode = network.factset.add_fact(con)
            fnode.ancestors.append(match.ancestor)
            neg = con.copy()
            neg.true = not neg.true
            contradiction = network.factset.query(neg)
            if contradiction:
                raise exceptions.Contradiction('we already have ' + str(neg))
            if network.root.child_path:
                m = Match(con)
                m.paths = network.factset.get_paths(con)
                m.fnode = fnode
                Node.dispatch(network.root, m, network)

    def get_pvar_map(self, match, prem):
        pvar_map = []
        for name, val in match.items():
            try:
                pvar = self.pvars.filter(PVarname.prem==prem).join(Varname, PVarname.varname_id==Varname.id).join(Term, Varname.term_id==Term.id).filter(Term.name==name).one()
            except NoResultFound:
                continue
            pvar_map.append((pvar.num, val))
        return pvar_map

    def get_varname(self, prem, num):
        pvar = self.pvars.filter(PVarname.prem==prem, PVarname.num==num).one()
        return pvar.varname.name


class PVarname(Base):
    """
    Mapping from varnames in rules (pvars belong in rules)
    to premise, number.
    Premises have numbered variables;
    and different rules can share a premise,
    but translate differently its numbrered vars to varnames.
    """
    __tablename__ = 'pvarnames'


    id = Column(Integer, Sequence('pvarname_id_seq'), primary_key=True)
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref=backref('pvars', lazy='dynamic'),
                         primaryjoin="Rule.id==PVarname.rule_id")
    prem_id = Column(Integer, ForeignKey('premises.id'))
    prem = relationship('Premise', backref=backref('pvars', lazy='dynamic'),
                         primaryjoin="Premise.id==PVarname.prem_id")
    varname_id = Column(Integer, ForeignKey('varnames.id'))
    varname = relationship('Varname', backref='pvarnames',
                         primaryjoin="Varname.id==PVarname.varname_id")
    num = Column(Integer)

    def __init__(self, prem, num, varname):
        self.prem = prem
        self.num = num
        self.varname = varname



class CondArg(Base):
    '''
    '''
    __tablename__ = 'condargs'

    id = Column(Integer, Sequence('condarg_id_seq'), primary_key=True)
    cond_id = Column(Integer, ForeignKey('conditions.id'))
    cond = relationship('Condition', backref='args',
                         primaryjoin="Condition.id==CondArg.cond_id")
    term_id = Column(Integer, ForeignKey('terms.id'))
    term = relationship('Term',
                         primaryjoin="Term.id==CondArg.term_id")

    def __init__(self, term):
        self.term = term

    def solve(self, match):
        if self.term.var:
            return match[self.term.name]
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

    ctype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': ctype}

    def __init__(self, *args):
        for arg in args:
            self.args.append(CondArg(arg))


class CondIsa(Condition):
    __tablename__ = 'condisas'
    __mapper_args__ = {'polymorphic_identity': 0}
    cid = Column(Integer, ForeignKey('conditions.id'), primary_key=True)

    def test(self, match, network):
        return isa(self.args[0].solve(match), self.args[1].solve(match))


class CondIs(Condition):
    __tablename__ = 'condiss'
    __mapper_args__ = {'polymorphic_identity': 1}
    cid = Column(Integer, ForeignKey('conditions.id'), primary_key=True)

    def test(self, match, network):
        return are(self.args[0].solve(match), self.args[1].solve(match))


class CondCode(Condition):
    __tablename__ = 'condcodes'
    __mapper_args__ = {'polymorphic_identity': 2}
    cid = Column(Integer, ForeignKey('conditions.id'), primary_key=True)

    code = Column(String)

    def test(self, match, network):
        match['condition'] = True
        for k, v in match.items():
            if getattr(v, 'number', False):
                match[k] = eval(v.name)
        try:
            exec(self.code, {}, match)
        except Exception as e:
            if match['condition']:
                raise
            return False

        for k, v in match.items():
            if k == 'condition':
                continue
            try:
                match[k] = network.lexicon.make_term(str(0 + v), network.lexicon.number)
            except TypeError:
                pass
        return match['condition']

    def __init__(self, code):
        self.code = code
