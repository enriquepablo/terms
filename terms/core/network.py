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

import time

from sqlalchemy import Column, Sequence, Index
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import InvalidRequestError

from terms.core import exec_globals
from terms.core.terms import isa, are, get_bases
from terms.core.terms import Base, Term, term_to_base, Predicate
from terms.core.lexicon import Lexicon
from terms.core.factset import FactSet, Ancestor
from terms.core import exceptions
from terms.core.utils import Match, merge_submatches


class Network(object):

    def __init__(self, session, config):
        self.session = session
        self.config = config
        self.activations = []
        self.root = self.session.query(RootNode).one()
        self.lexicon = Lexicon(session, config)
        self.present = FactSet('present', self.lexicon, config)
        self.past = FactSet('past', self.lexicon, config)

    @classmethod
    def initialize(self, session):
        Base.metadata.create_all(session.connection().engine)
        try:
            session.query(RootNode).one()
        except NoResultFound:
            root = RootNode()
            session.add(root)
            Lexicon.initialize(session)

    def passtime(self):
        past = eval(self.now, {}, {})
        now = 0
        if self.config['time'] == 'normal':
            now = past + 1
        elif self.config['time'] == 'real':
            now = int(time.time())
        self.now = now

    def _get_now(self):
        return str(self.lexicon.time.now)

    def _set_now(self, val):
        self.lexicon.time.now = eval(str(val), {}, {})
        now = str(0 + self.lexicon.time.now)
        self.lexicon.now_term = self.lexicon.make_term(now, self.lexicon.number)

    now = property(_get_now, _set_now)

    def get_paths(self, pred):
        '''
        build a path for each testable feature in term.
        Each path is a tuple of strings,
        and corresponds to a node in the primary network.
        '''
        paths = []
        verb_ = pred.term_type
        self._recurse_paths(verb_, pred, paths, (), first=True)
        return paths

    def _recurse_paths(self, verb_, pred, paths, path, first=False):
        paths.append(path + ('_verb',))
        paths.append(path + ('_neg',))
        for obt in sorted(verb_.object_types, key=lambda x: x.label):
            # XXX this would serve only for the present
            if obt.label in ('till_', 'since_', 'at_'):
                continue
            t = obt.obj_type
            if isa(t, self.lexicon.verb):
                pred = pred.get_object(obt.label)
                verb_ = pred.term_type
                self._recurse_paths(verb_, pred, paths, path + (obt.label,))
            else:
                paths.append(path + (obt.label, '_term'))

    def _get_nclass(self, ntype):
        mapper = Node.__mapper__
        return mapper.base_mapper.polymorphic_map[ntype].class_

    def add_fact(self, pred):
        factset = self.present
        if isa(pred, self.lexicon.onwards):
            pred.add_object('since_', self.lexicon.now_term)
        neg = pred.copy()
        neg.true = not neg.true
        contradiction = factset.query(neg)
        if contradiction:
            raise exceptions.Contradiction('we already have ' + str(neg))
        prev = factset.query_facts(pred, {}).all()
        fact = factset.add_fact(pred, prev)
        ancestor = Ancestor(fact)
        ancestor.children.append(fact)
        if prev:
            return prev[0]
        if self.root.child_path:
            m = Match(pred)
            m.paths = self.get_paths(pred)
            m.fact = fact
            Node.dispatch(self.root, m, self)
        while self.activations:
            match = self.activations.pop()
            Node.dispatch(self.root, match, self)
        return fact

    def unsupported_descent(self, fact, descent=None):
        if descent is None:
            descent = []
        for descendant in fact.descent:
            for ch in descendant.children:
                if ch is fact:
                    continue
                if len(ch.ancestors) == 1:
                    descent.append(ch)
                    self.unsupported_descent(ch, descent)
                else:
                    ch.ancestors.remove(descendant)
        return descent

    def finish(self, pred):
        fact = self.present.query_facts(pred, []).one()
        tofinish = self.unsupported_descent(fact) + [fact]
        for f in tofinish:
            pred = f.pred
            self.present.add_object_to_fact(f, self.lexicon.now_term, ('till_', '_term'))
            f.factset = 'past'
            f.matches = []

    def del_fact(self, pred):
        fact = self.present.query_facts(pred, []).one()
        if not isa(pred, self.lexicon.onwards):
            for a in fact.ancestors:
                if not (len(a.parents) == 1 and a.parents[0].id == fact.id):
                    raise exceptions.Contradiction('Cannot retract ' + str(fact.pred))
        descent = self.unsupported_descent(fact)
        self.session.delete(fact)
        for ch in descent:
            self.session.delete(ch)

    def add_rule(self, prems, conds, cons, finishes):
        rule = Rule()
        for n, pred in enumerate(prems):
            vars = {}
            paths = self.get_paths(pred)
            old_node = self.root
            for path in paths:
                old_node = self.get_or_create_node(old_node, pred, path, vars, rule)
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
        for finish in finishes:
            rule.finishes.append(finish)
        for prem in rule.prems:
            matches = self.present.query(prem.pred)
            for match in matches:
                prem.dispatch(match, self, _numvars=False)


    def query(self, *q):
        submatches = []
        for pred in q:
            factset = self.present
            if isa(pred, self.lexicon.now):
                factset = self.past
            smatches = factset.query(pred)
            submatches.append(smatches)
        matches = merge_submatches(submatches)
        unique = []
        for m in matches:
            for m2 in unique:
                if m2 == m:
                    break
            else:
                unique.append(m)
        return unique

    def get_or_create_node(self, parent, term, path, vars, rule):
        ntype_name = path[-1]
        cls = self._get_nclass(ntype_name)
        value = cls.resolve(term, path)
        name = getattr(value, 'name', '')
        is_var = getattr(value, 'var', False)
        pnum = 0
        if is_var:
            if name not in vars:
                pnum = len(vars) + 1
                vars[name] = (pnum, Varname(value, rule))
            else:
                pnum = vars[name][0]
        try:
            nodes = self.session.query(cls).filter(cls.parent_id==parent.id, cls.var==pnum)
            node = nodes.filter(cls.value==value).one()
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
    var = Column(Integer, default=0, index=True)
    parent_id = Column(Integer, ForeignKey('nodes.id'), index=True)
    children = relationship('Node',
                         backref=backref('parent',
                                         uselist=False,
                                         remote_side=[id]),
                         primaryjoin="Node.id==Node.parent_id",
                         cascade='all',
                         lazy='dynamic')

    ntype = Column(String)
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
    def resolve(cls, pred, path):
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
            value = chcls.resolve(match.pred, path)
            children = chcls.get_children(parent, value, network)
            for ch in children:
                for child in ch:
                    new_match = match.copy()
                    if child.var:
                        val = None
                        if chcls is VerbNode and isa(child.value, network.lexicon.exists):
                            val = TermNode.resolve(match.pred, path)
                        else:
                            val = value
                        new_match[child.var] = val
                    chcls.dispatch(child, new_match, network)
        if parent.terminal:
            parent.terminal.dispatch(match, network)

    @classmethod
    def get_children(cls, parent, value, factset):
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
    __mapper_args__ = {'polymorphic_identity': '_root'}

    def __init__(self):
        pass


class NegNode(Node):
    '''
    A node that tests whether a predicate is negated
    '''
    __mapper_args__ = {'polymorphic_identity': '_neg'}

    value = Column(Boolean, index=True)
    
    @classmethod
    def resolve(cls, pred, path):
        for segment in path[:-1]:
            pred = pred.get_object(segment)
        try:
            return pred.true
        except AttributeError:
            # Predicate variable
            return True

    @classmethod
    def get_children(cls, parent, value, network):
        return [network.session.query(cls).filter(cls.parent_id==parent.id, (cls.value==value) | (cls.value==None))]


class TermNode(Node):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': '_term'}
    term_id = Column(Integer, ForeignKey('terms.id'), index=True)
    value = relationship('Term', primaryjoin="Term.id==TermNode.term_id")
    
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
    def get_children(cls, parent, value, network):
        children = network.session.query(cls).filter(cls.parent_id==parent.id, (cls.value==value) | (cls.value==None))
        vchildren = ()
        types = (value.term_type,) + get_bases(value.term_type)
        type_ids = [t.id for t in types]
        if type_ids:
            vchildren = network.session.query(cls).filter(cls.parent_id==parent.id).join(Term, cls.term_id==Term.id).filter(Term.var==True).filter(Term.type_id.in_(type_ids))
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
    __mapper_args__ = {'polymorphic_identity': '_verb'}
    verb_id = Column(Integer, ForeignKey('terms.id'), index=True)
    value = relationship('Term', primaryjoin="Term.id==VerbNode.verb_id")
    
    @classmethod
    def resolve(cls, term, path):
        for segment in path[:-1]:
            term = term.get_object(segment)
        if term.var:
            return term
        return term.term_type

    @classmethod
    def get_children(cls, parent, value, network):
        children = network.session.query(cls).filter(cls.parent_id==parent.id, (cls.value==value) | (cls.value==None))
        pchildren = []
        types = (value,) + get_bases(value)
        type_ids = [t.id for t in types]
        chvars = network.session.query(cls).filter(cls.parent_id==parent.id, Node.var>0)
        pchildren = chvars.join(Term, cls.verb_id==Term.id).filter(Term.type_id.in_(type_ids))
        tbases = aliased(Term)
        vchildren = chvars.join(Term, cls.verb_id==Term.id).join(term_to_base, Term.id==term_to_base.c.term_id).join(tbases, term_to_base.c.base_id==tbases.id).filter(tbases.id.in_(type_ids))
        return children, pchildren, vchildren


class PremNode(Base):
    '''
    a terminal node for a premise
    '''
    __tablename__ = 'premnodes'

    id = Column(Integer, Sequence('premnode_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('nodes.id'), index=True)
    parent = relationship('Node', backref=backref('terminal', uselist=False),
                         primaryjoin="Node.id==PremNode.parent_id")

    def __init__(self, parent):
        self.parent = parent  # node

    def dispatch(self, match, network, _numvars=True):
        if not self.prems[0].check_match(match, network):
            return
        m = PMatch(self, match.fact)
        for var, val in match.items():
            m.pairs.append(MPair.make_pair(var, val))
        self.matches.append(m)
        match.ancestor = Ancestor(match.fact)
        for premise in self.prems:
            premise.dispatch(match, network, _numvars=_numvars)


class Premise(Base):
    '''
    Relation between rules and premnodes
    '''
    __tablename__ = 'premises'

    id = Column(Integer, Sequence('premise_id_seq'), primary_key=True)
    prem_id = Column(Integer, ForeignKey('premnodes.id'), index=True)
    node = relationship('PremNode', backref='prems', 
                         primaryjoin="PremNode.id==Premise.prem_id")
    rule_id = Column(Integer, ForeignKey('rules.id'), index=True)
    rule = relationship('Rule', backref=backref('prems', lazy='dynamic'),
                         primaryjoin="Rule.id==Premise.rule_id")
    pred_id = Column(Integer, ForeignKey('predicates.id'), index=True)
    pred = relationship('Predicate',
                         primaryjoin="Predicate.id==Premise.pred_id")
    order = Column(Integer)

    def __init__(self, pnode, order, pred):
        self.node = pnode
        self.order = order
        self.pred = pred

    def check_match(self, match, network):
        pred = self.pred
        prem_paths = network.present.get_paths(pred)
        for p in prem_paths:
            if p not in match.paths:
                return False
        return True

    def dispatch(self, match, network, _numvars=True):
        rule = self.rule
        if _numvars:
            nmatch = match.copy()
            for num, o in match.items():
                pvar = tuple(filter(lambda x: x.rule==rule and x.num==num, self.pvars))[0]
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
                    if not isa(pm.fact.pred, network.lexicon.now):
                        try:
                            new_match.ancestor.parents.append(pm.fact)
                        except AttributeError:
                            new_match.ancestor = Ancestor(pm.fact)
                    for mpair in pm.pairs:
                        vname = rule.get_varname(prem, mpair.var)
                        if vname in m:
                            assert m[vname] == mpair.val
                        else:
                            new_match[vname] = mpair.val
                    new_matches.append(new_match)
            matches = new_matches
        for m in matches:
            rule.dispatch(m, network)


class PMatch(Base):
    __tablename__ = 'pmatchs'

    id = Column(Integer, Sequence('pmatch_id_seq'), primary_key=True)
    prem_id = Column(Integer, ForeignKey('premnodes.id'), index=True)
    prem = relationship('PremNode', backref=backref('matches', lazy='dynamic'),
                         primaryjoin="PremNode.id==PMatch.prem_id")
    fact_id = Column(Integer, ForeignKey('facts.id'), index=True)
    fact = relationship('Fact', backref=backref('matches', cascade='all,delete-orphan'),
                         primaryjoin="Fact.id==PMatch.fact_id")

    def __init__(self, prem, fact):
        self.prem = prem
        self.fact = fact


class MPair(Base):
    __tablename__ = 'mpairs'

    id = Column(Integer, Sequence('mpair_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('pmatchs.id'), index=True)
    parent = relationship('PMatch', backref=backref('pairs', cascade='all'),
                         primaryjoin="PMatch.id==MPair.parent_id")
    var = Column(Integer, index=True)
    mindex = Index('mindex', 'id', 'parent_id')

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
    term_id = Column(Integer, ForeignKey('terms.id'), index=True)
    val = relationship('Term', primaryjoin="Term.id==TPair.term_id")
    tindex = Index('tindex', 'mid', 'term_id')


class PPair(MPair):
    __tablename__ = 'ppairs'
    __mapper_args__ = {'polymorphic_identity': 1}
    mid = Column(Integer, ForeignKey('mpairs.id'), primary_key=True)
    pred_id = Column(Integer, ForeignKey('predicates.id'), index=True)
    val = relationship('Predicate',
                         primaryjoin="Predicate.id==PPair.pred_id")
    pindex = Index('pindex', 'mid', 'pred_id')


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
    rule_id = Column(Integer, ForeignKey('rules.id'), index=True)
    rule = relationship('Rule', backref=backref('pvars', lazy='joined'),
                         primaryjoin="Rule.id==PVarname.rule_id")
    prem_id = Column(Integer, ForeignKey('premises.id'), index=True)
    prem = relationship('Premise', backref=backref('pvars', lazy='joined'),
                         primaryjoin="Premise.id==PVarname.prem_id")
    varname_id = Column(Integer, ForeignKey('varnames.id'), index=True)
    varname = relationship('Varname', backref='pvarnames',
                         lazy='joined',
                         primaryjoin="Varname.id==PVarname.varname_id")
    num = Column(Integer, index=True)

    def __init__(self, prem, num, varname):
        self.prem = prem
        self.num = num
        self.varname = varname


class Varname(Base):
    """
    a variable in a rule,
    it has a name
    """
    __tablename__ = 'varnames'

    id = Column(Integer, Sequence('varname_id_seq'), primary_key=True)
    rule_id = Column(Integer, ForeignKey('rules.id'), index=True)
    rule = relationship('Rule', backref=backref('varnames', lazy='joined'),
                         primaryjoin="Rule.id==Varname.rule_id")
    term_id = Column(Integer, ForeignKey('terms.id'), index=True)
    var = relationship('Term', backref='varnames',
                         lazy='joined',
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

        for finish in self.finishes:
            tofinish = finish.pred.substitute(match)
            network.finish(tofinish)

        cons = []
        for con in self.consecuences:
            cons.append(con.substitute(match))

        for con in self.vconsecuences:
            cons.append(match[con.name])

        for con in cons:
            factset = network.present
            if isa(con, network.lexicon.onwards):
                con.add_object('since_', network.lexicon.now_term)
            neg = con.copy()
            neg.true = not neg.true
            contradiction = factset.query(neg)
            if contradiction:
                raise exceptions.Contradiction('we already have ' + str(neg))
            prev = factset.query_facts(con, {}).all()
            fact = factset.add_fact(con, prev)
            if match.ancestor:
                try:
                    fact.ancestors.append(match.ancestor)
                except InvalidRequestError:
                    pass
            if prev:
                continue
            if network.root.child_path:
                m = Match(con)
                m.paths = network.get_paths(con)
                m.fact = fact
                network.activations.append(m)

    def get_pvar_map(self, match, prem):
        pvar_map = []
        for name, val in match.items():
            pvars = filter(lambda x: x.prem==prem and x.varname.var.name==name, self.pvars)
            for n, pvar in enumerate(pvars):
                pvar_map.append((pvar.num, val))
                if n > 1:
                    raise exceptions.Corruption('should not happen')
        return pvar_map

    def get_varname(self, prem, num):
        pvar = tuple(filter(lambda x: x.prem==prem and x.num==num, self.pvars))[0]
        return pvar.varname.name


class CondArg(Base):
    '''
    '''
    __tablename__ = 'condargs'

    id = Column(Integer, Sequence('condarg_id_seq'), primary_key=True)
    cond_id = Column(Integer, ForeignKey('conditions.id'), index=True)
    cond = relationship('Condition', backref='args',
                         primaryjoin="Condition.id==CondArg.cond_id")
    term_id = Column(Integer, ForeignKey('terms.id'), index=True)
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
    rule_id = Column(Integer, ForeignKey('rules.id'), index=True)
    rule = relationship('Rule', backref='conditions',
                         primaryjoin="Rule.id==Condition.rule_id")

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
        exec_locals = {'condition': True}
        exec_locals.update(exec_globals)
        for k, v in match.items():
            if getattr(v, 'number', False):
                exec_locals[k] = eval(v.name, {}, {})
            else:
                exec_locals[k] = v
        try:
            exec(self.code, {}, exec_locals)
        except Exception:
            if exec_locals['condition']:
                raise
            return False

        for k, v in exec_locals.items():
            if k in ('condition', '__builtins__') or k in exec_globals:
                continue
            try:
                match[k] = network.lexicon.make_term(str(0 + v), network.lexicon.number)
            except TypeError:
                pass
        return exec_locals['condition']

    def __init__(self, code):
        self.code = code


class Finish(Base):
    __tablename__ = 'finishs'

    id = Column(Integer, Sequence('finish_id_seq'), primary_key=True)
    rule_id = Column(Integer, ForeignKey('rules.id'), index=True)
    rule = relationship('Rule', backref='finishes',
                         primaryjoin="Rule.id==Finish.rule_id")
    pred_id = Column(Integer, ForeignKey('predicates.id'), index=True)
    pred = relationship('Predicate', primaryjoin="Predicate.id==Finish.pred_id")

    def __init__(self, pred):
        self.pred = pred
