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


special_resolvers = {}


def resolve(sen, path):
    '''
    Get the value (a string) in sen (a StringSentence)
    pointed at by path (a string).
    '''
    obj = sen
    path = path.split('.')
    for segment in path:
        if segment in special_resolvers:
            obj = 


class Match(object):
    def __init__(self, sen):
        self.sen = sen
        self.substitutions = {}  # varname -> term
        self.prem = None

    def copy(self, node=None):
        new_match = Match(self.sen)
        new_match.substitutions = {k: v for k, v in self.substitutions.items()}
        new_match.prem = node or self.prem
        return new_match


class TermNode(object):
    def __init__(self, path, pred, term, var):
        self.path = path  # string
        self.pred = pred  # string
        self.term = term  # term
        self.var = var  # int
        self.type = 'arg'  # pred/arg to discriminate PredNodes / ArgNodes

    def test(self, match):
        """
        test the sentence in match against this node.

        return a new match for success
        or None for failure
        """
        term = resolve(match.sen, self.path)
        if self.var in match.substitutions:
            if match.substitutions[self.var] is term:
                return match.copy(self)
        elif self.pred(term, self.term):
            new_match = match.copy(self)
            if self.var:
                new_match.substitutions[self.var] = term
            return new_match


    def dispatch(self, match):
        for child in self.children:
            new_match = child.test(match)
            if new_match:
                child.dispatch(new_match)


class PredNode(TermNode):
    # discriminate on self.type

    def __init__(self, true, *args):
        self.true = true
        super(PredNode, self).__init__(*args)


class ArgNode(TermNode):
    '''
    '''
    # discriminate on self.type


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
    def __init__(self, name):
        self.name = name


class idict(dict):
    def __setitem__(self, k, v):
        if k not in self:
            super(idict, self).__setitem__(k, v)


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
        self.args = args  # terms. terms have conversors for different funs

    def test(self, match):
        sargs = []
        for arg in args:
            sargs.append(arg.resolve(match))
        return self.fun(*sargs)


class Rule(TermNode, MNodeDispatcher):

    def __init__(self, network):
        self.network = network
        self.prems = []  # nodes
        self.pvars = []  # pvars
        self.vrs = []  # string
        self.network = []  # mnodes
        self.conditions = []  # conditions
        self.cons = []  # consecuences

    def test(self, match):
        return match

    def dispatch(self, match):
        old_matches = []
        if not self.children:
            if len(match.substitutions) == len(self.rule.vrs):
                matches = [match]
            else:
                self.add_mnodes(match, old_matches)
                matches = []
        else:
            matches = self.dispatch_to_children(match, old_matches)

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

    def add_mnodes(self, match):
        self._add_mnodes(match, [], self)

    def add_term_prem(self, prem):
        '''
        prem is a StringSentence
        '''


class Network(object):
    
    def __init__(self, kb):
        self.kb = kb

    def add_fact(self, fact):
        m = Match(fact)
        self.root.dispatch(m)
        self.kb.factset.add_fact(fact)

    def add_rule(self, prems, cons):
        pass


class StringSentence(object):
    '''
    Consecuences in rules.
    Also used as intermediate values for predicates
    and premises by the compiler
    '''
    def __init__(self, true, verb, **args):
        '''
        verb is a string.
        args is a dict with strings (labels) to strings (terms)
        '''
        self.true = true  # boolean
        self.verb = verb  # string
        self.args = []  # StringObjects
        for k, v in args.items():
            self.args.append(StringObject(k, v))


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
