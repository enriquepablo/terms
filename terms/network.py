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


node_types = []

node_type_names = {}


def register(tname):
    def fun(nodeclass):
        n = len(node_types)
        node_type_names[tname] = n
        node_types.append(nodeclass)
        nodeclass.tname = tname
        return nodeclass
    return fun

def get_tnode(tname):
    if isinstance(tname, int):
        return node_types[tname]
    else:
        return node_types[node_type_names[tname]]

def get_tnum(tname):
        return node_type_names[tname]

def get_ntype(w):
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
    paths = []
    recurse_paths(w, paths, ())
    return paths

def recurse_paths(pred, paths, path):
    paths.append(path + ('neg',))
    paths.append(path + ('verb',))
    for l, o in pred.args:
        paths.append(path + (l, 'label'))
        if isinstance(o, exists):
            recurse_paths(o, paths, path + (l,))
        else:
            paths.append(path + (l,))

def resolve(sen, path):
    '''
    Get the value (a string) in sen (a StringSentence)
    pointed at by path (a string).
    '''
    obj = sen
    for segment in path:
        if segment in special_resolvers:
            obj = special_resolvers[segment](obj, path)
        else:
            obj = getattr(obj, segment, None)
    return obj

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


class Match(object):
    def __init__(self, sen):
        self.fact = fact  # Predicate
        self.substitutions = {}  # varname -> term
        self.prem = None

    def copy(self, node=None):
        new_match = Match(self.fact)
        new_match.substitutions = {k: v for k, v in self.substitutions.items()}
        new_match.prem = node or self.prem
        return new_match


class Node(object):

    T_NEG = 0
    T_SET = 1
    T_LABEL = 2
    T_ELEM = 3

    def __init__(self, path, var=0, t=T_ELEM):
        self.path = path  # string
        self.var = var  # int
        self.type = t  # pred/arg/prem to discriminate PredNodes / ArgNodes / PremNodes
        self.children = []  # nodes
        self.pchildren = []  # prem nodes

    def filter_siblings(self, parent, match):
        raise NotImplementedError

    def dispatch(self, match):
        if self.var:
            if self.var in match.subs:
                if match.subs[self.var] != self.get_val():
                    return
            else:
                match.subs[self.var] = self.get_val()
        if self.children:
            children = self.children[0].filter_siblings(self, match)
            for child in children:
                new_match = match.copy()
                child.dispatch(new_match)
        if self.pchildren:
            for p in self.pchildren:
                new_match = match.copy()
                p.dispatch(new_match)

    def get_val(self):
        raise NotImplementedError

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        raise NotImplementedError


@register('_neg')
class NegNode(Node):

    def __init__(self, true, *args, **kwargs):
        self.true = true
        super(NegNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        true = resolve(match.sen, self.path)
        if true == self.true:
            return (self,)
        return (parent.children[1],)

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        try:
            return parent.children.filter(true=w).one()
        except NotFound:
            pass
        #  build the node and append it
        node = NegNode(true, path, t=get_type_num(cls.tname))
        parent.children.append(node)
        return node


@register('_set')
class SetNode(TermNode):
    # discriminate on self.type

    def __init__(self, term, *args, **kwargs):
        self.term = term
        super(SetNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        w = resolve(match.sen, self.path)
        words = lexicon.get_subwords(w)
        return parent.children.filter(val_or=[|w for w in words], var=w.var)

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
            return parent.children.filter(term=term, var=var).one()
        except NotFound:
            pass
        #  build the node and append it
        node = SetNode(term, path, var=var, t=get_type_num(cls.tname))
        parent.children.append(node)
        return node

@register('_elem')
class NameNode(TermNode):

    def __init__(self, term, *args, **kwargs):
        self.term = term
        super(NameNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        w = resolve(match.sen, self.path)
        return parent.children.filter(term=lexicon.get_term(w), var=w.var)

    def get_val(self):
        return self.term

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        '''
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
            return parent.children.filter(term=term, var=var).one()
        except NotFound:
            pass
        #  build the node and append it
        node = NameNode(term, path, var=var, t=get_type_num(cls.tname))
        parent.children.append(node)
        return node


@register('_label')
class LabelNode(TermNode):

    def __init__(self, label, *args, **kwargs):
        self.label = label
        super(LabelNode, self).__init__(*args, **kwargs)

    def filter_siblings(self, parent, match):
        w = resolve(match.sen, self.path)
        sibs = []
        for sib in parent.children:
            if hasattr(w, sib.label):
                sibs.append(sib)
        return sibs

    @classmethod
    def get_node(cls, parent, w, path, var_map):
        try:
            return parent.children.filter(label=w).one()
        except NotFound:
            pass
        #  build the node and append it
        node = LabelNode(w, path, t=get_tnum(cls.tname))
        parent.children.append(node)
        return node


class PremNode(TermNode):
    '''
    a terminal node for a premise
    '''

    def dispatch(self, match):
        match.prem = self
        for child in self.children:
            new_match = match.copy()
            child.dispatch(new_match)


class MNodeDispatcher(object):

    def dispatch_to_children(self, match, old_matches):
        if not self.children:
            return []
        new_matches = []
        first = self.children.first()
        # matching = self.children.filter(value=new_match.substitutions[first.var])
        # for child in matching:
        for child in self.children:
            new_matches.append(child.dispatch(match, old_matches))
        new_matches = filter(lambda x: x is not None, new_matches)
        if not new_matches:
            self.add_mnodes(match, old_matches, hint=first.var)
        return [m for matches in new_matches for m in matches]

    def _add_mnodes(self, match, old_matches, rule, hint=None):
        if not hint:
            left = filter(lambda x: x not in old_matches, match.substitutions.keys())
            if not left:
                return
            hint = left[0]
        mnode = MNode(hint, match.substitutions[hint], rule)
        self.children.append(mnode)
        old_matches.append(hint)
        mnode.add_mnodes(match, old_matches)


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
        if old_matches is None:
            old_matches = []
        prev_val = match.substitutions.get(self.var, None)
        new_match = match.copy()
        if not prev_val:
            new_match.substitutions[self.var] = self.value
        elif prev_val != self.value:
            return
        old_matches_c = old_matches[:]
        old_matches_c.append(self.var)
        if not self.children:
            if len(new_match.substitutions) == len(self.rule.vrs):
                return [new_match]
            else:
                self.add_mnodes(new_match, old_matches_c)
                return []
        return self.dispatch_to_children(new_match, old_matches_c)

    def add_mnodes(self, match, old_matches, hint=None):
        self._add_mnodes(match, old_matches, self.rule, hint=None)


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
            old_node.pchildren.append(pnode)
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
