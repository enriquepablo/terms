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

from urllib.request import urlopen

import ply.lex as lex
import ply.yacc
from ply.lex import TOKEN


from sqlalchemy.orm.exc import NoResultFound

from terms.core.patterns import SYMBOL_PAT, VAR_PAT, NUM_PAT, QUOTED_SYMBOL_PAT
from terms.core.network import Network, CondIsa, CondIs, CondCode
from terms.core.terms import isa, Predicate, Import
from terms.core.exceptions import TermsSyntaxError, WrongObjectType, WrongLabel
from terms.core.exceptions import ImportProblems, DuplicateWord
from terms.core.exceptions import TermNotFound

import logging
logger = logging.getLogger(__name__)


class Lexer(object):

    states = (
        ('pycode', 'exclusive'),
        ('set', 'exclusive'),
        ('headers', 'exclusive'),
    )

    tokens = (
        'SYMBOL',
        'QSYMBOL',
        'NUMBER',
        'COMMA',
        'LPAREN',
        'RPAREN',
        'DOT',
        'QMARK',
        'NOT',
        'IS',
        'TO',
        'A',
        'SEMICOLON',
        'COLON',
        'VAR',
        'IMPLIES',
        'INSTANT_IMPLIES',
        'RM',
        'PYCODE',
        'HEADER',
        'IMPORT',
        'URL',
        'SVAR',
        'SCOLON',
        'SLPAREN',
        'SRPAREN',
        'SNUMBER',
        'SOPER',
        'SPRED',
        'SBAR',
        'SAMP',
        'SNOT',
    )

    reserved = {
        'is': 'IS',
        'to': 'TO',
        'a': 'A',
        'import': 'IMPORT',
    }

    t_NUMBER = NUM_PAT
    t_COMMA = r','
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_DOT = r'\.'
    t_QMARK = r'\?'
    t_NOT = r'!'
    t_SEMICOLON = r';'
    t_COLON = r':'
    t_VAR = VAR_PAT
    t_INSTANT_IMPLIES = r'-->'
    t_IMPLIES = r'->'
    t_RM = r'_RM_'
    t_URL = r'<[^>]+>'

    t_set_SVAR = VAR_PAT
    t_set_SCOLON = r':'
    t_set_SLPAREN = r'\('
    t_set_SRPAREN = r'\)'
    t_set_SNUMBER = NUM_PAT
    t_set_SOPER = r'[*/+%-]'
    t_set_SPRED = r'[<>=!]=?'
    t_set_SBAR = r'\|'
    t_set_SAMP = r'&'
    t_set_SNOT = r'~'

    @TOKEN(QUOTED_SYMBOL_PAT)
    def t_QSYMBOL(self, t):
        # Check for reserved words
        t.type = self.reserved.get(t.value, 'QSYMBOL')
        return t

    @TOKEN(SYMBOL_PAT)
    def t_SYMBOL(self, t):
        # Check for reserved words
        t.type = self.reserved.get(t.value, 'SYMBOL')
        return t

    # Define a rule so we can track line numbers
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # A string containing ignored characters (spaces and tabs)
    t_ignore = ' \t'

    def t_begin_pycode(self, t):
        r'<-'
        t.lexer.begin('pycode')

    # Define a rule so we can track line numbers
    def t_pycode_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_pycode_IMPLIES(self, t):
        r'->'
        t.lexer.begin('INITIAL')
        return t

    # Any sequence of characters
    def t_pycode_PYCODE(self, t):
        r'.+'
        return t

    t_pycode_ignore = ''

    def t_begin_set(self, t):
        r'(?<=[^{]){(?=[^{])'
        t.lexer.begin('set')

    def t_set_RCURLY(self, t):
        r' }'
        t.lexer.begin('INITIAL')

    t_set_ignore = ' \t'

    def t_begin_headers(self, t):
        r'{{{'
        t.lexer.begin('headers')

    # Define a rule so we can track line numbers
    def t_headers_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_headers_close(self, t):
        r'}}}'
        t.lexer.begin('INITIAL')

    # Any sequence of characters
    def t_headers_HEADER(self, t):
        r'.+'
        return t

    t_headers_ignore = ''

    # Error handling rule
    def t_set_headers_pycode_INITIAL_error(self, t):
        logger.info("Illegal character '%s' at line %d" % (t.value[0], t.lexer.lineno))
        t.lexer.skip(1)

    # Build the lexer
    def build(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)

    # Test it output
    def test(self, data):
        self.lexer.input(data)
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            print(tok)


class Parser(object):

    precedence = (
        ('left', 'COMMA'),
        ('left', 'LPAREN'),
        ('left', 'SEMICOLON'),
    )

    def __init__(
            self,
            lex_optimize=False,
            yacc_optimize=True,
            yacc_debug=False):

        self.lex = Lexer()

        self.lex.build(
            optimize=lex_optimize)
        self.tokens = self.lex.tokens

        self.parser = ply.yacc.yacc(
            module=self,
            start='module',
            write_tables=False,
            debug=yacc_debug,
            optimize=yacc_optimize)

    def parse(self, text, filename='', debuglevel=0):
        """
            text:
                A string containing the source code

            filename:
                Name of the file being parsed (for meaningful
                error messages)

            debuglevel:
                Debug level to yacc
        """
        self.lex.filename = filename
        # self.lex.reset_lineno()
        return self.parser.parse(text, lexer=self.lex.lexer, debug=debuglevel)

    # BNF

    def p_module(self, p):
        '''module : URL headers constructs
                  | URL constructs
                  | constructs'''
        url, headers, code = None, None, ''
        if len(p) >= 3:
            url = p[1][1:-1]
            if len(p) == 4:
                headers = p[2]
                code = p[3]
            else:
                code = p[2]
        else:
            code = p[1]
        p[0] = AstNode('module', url=url, headers=headers, code=code)

    def p_headers(self, p):
        '''headers : HEADER headers
                   | HEADER'''
        if len(p) == 3:
            p[0] = (p[1],) + p[2]
        else:
            p[0] = (p[1],)

    def p_constructs(self, p):
        '''constructs : construct constructs
                      | construct'''
        if len(p) == 3:
            p[0] = p[2]
            p[0].append(p[1])
        else:
            p[0] = [p[1]]

    def p_construct(self, p):
        '''construct : definition
                     | rule
                     | instant-rule
                     | fact-set
                     | question
                     | removal
                     | import'''
        p[0] = p[1]

    def p_fact_set(self, p):
        '''fact-set : fact-list DOT'''
        p[0] = AstNode('fact-set', facts=p[1])

    def p_definition(self, p):
        '''definition : def DOT'''
        p[0] = AstNode('definition', definition=p[1])

    def p_question(self, p):
        '''question : sentence-list QMARK'''
        p[0] = AstNode('question', facts=p[1])

    def p_removal(self, p):
        '''removal : RM fact-list DOT'''
        p[0] = AstNode('removal', facts=p[2])

    def p_import(self, p):
        '''import : IMPORT URL DOT'''
        p[0] = AstNode('import', url=p[2][1:-1])

    def p_instant_rule(self, p):
        '''instant-rule : sentence-list INSTANT_IMPLIES sentence-list DOT
                        | sentence-list pylines INSTANT_IMPLIES sentence-list DOT'''
        if len(p) == 6:
            pycode = '\n'.join(p[2]).strip()
            p[0] = AstNode('instant-rule', prems=p[1], pycode=pycode, cons=p[4])
        else:
            p[0] = AstNode('instant-rule', prems=p[1], pycode='', cons=p[3])

    def p_rule(self, p):
        '''rule : sentence-list IMPLIES sentence-list DOT
                | sentence-list pylines IMPLIES sentence-list DOT'''
        if len(p) == 6:
            pycode = '\n'.join(p[2]).strip()
            p[0] = AstNode('rule', prems=p[1], pycode=pycode, cons=p[4])
        else:
            p[0] = AstNode('rule', prems=p[1], pycode='', cons=p[3])

    def p_pylines(self, p):
        '''pylines : PYCODE pylines
                   | PYCODE'''
        if len(p) == 3:
            p[0] = (p[1],) + p[2]
        else:
            p[0] = (p[1],)

    def p_fact_list(self, p):
        '''fact-list : fact SEMICOLON fact-list
                     | fact'''
        if len(p) == 4:
            p[0] = (p[1],) + p[3]
        else:
            p[0] = (p[1],)

    def p_sentence_list(self, p):
        '''sentence-list : sentence SEMICOLON sentence-list
                         | sentence'''
        if len(p) == 4:
            p[0] = (p[1],) + p[3]
        else:
            p[0] = (p[1],)

    def p_sentence(self, p):
        '''sentence : def
                    | fact'''
        p[0] = p[1]

    def p_fact(self, p):
        '''fact : prefact
                | var COLON prefact'''
        if len(p) == 4:
            p[3].predvar = p[1]
            p[0] = p[3]
        else:
            p[1].predvar = None
            p[0] = p[1]

    def p_prefact(self, p):
        '''prefact : LPAREN predicate RPAREN
                   | LPAREN NOT predicate RPAREN'''
        if len(p) == 5:
            p[0] = AstNode('fact', predicate=p[3], true=False)
        else:
            p[0] = AstNode('fact', predicate=p[2], true=True)

    def p_predicate(self, p):
        '''predicate : var
                     | verb object
                     | verb object COMMA mods'''
        if len(p) == 2:
            p[0] = AstNode('predicate', verb=p[1], subj=None, mods=())
        elif len(p) == 3:
            p[0] = AstNode('predicate', verb=p[1], subj=p[2], mods=())
        else:
            p[0] = AstNode('predicate', verb=p[1], subj=p[2], mods=p[4])

    def p_verb(self, p):
        '''verb : vterm'''
        p[0] = p[1]

    def p_vterm(self, p):
        '''vterm : term
                 | var'''
        p[0] = p[1]

    def p_vterms(self, p):
        '''vterms : vterm COLON vterms
                  | vterm'''
        if len(p) == 4:
            p[0] = p[3] + (p[1],)
        else:
            p[0] = (p[1],)

    def p_term(self, p):
        '''term : SYMBOL
                | QSYMBOL'''
        p[0] = AstNode('term', val=p[1])

    def p_var(self, p):
        '''var : VAR'''
        p[0] = AstNode('var', val=p[1])

    def p_number(self, p):
        '''number : NUMBER'''
        p[0] = AstNode('number', val=p[1])

    def p_mods(self, p):
        '''mods : mod COMMA mods
                | mod'''
        if len(p) == 4:
            p[0] = p[3] + (p[1],)
        else:
            p[0] = (p[1],)

    def p_mod(self, p):
        '''mod : SYMBOL object'''
        p[0] = AstNode('mod', label=p[1], obj=p[2])

    def p_object(self, p):
        '''object : vterm
                  | fact
                  | number
                  | set'''
        p[0] = p[1]

    def p_set(self, p):
        '''set : SVAR SCOLON s-expr'''
        p[0] = AstNode('set', var=p[1], stmnt=p[3])

    def p_snumber(self, p):
        '''s-number : SNUMBER'''
        p[0] = AstNode('s-vnum', val=p[1], var=False)

    def p_svar(self, p):
        '''s-var : SVAR'''
        p[0] = AstNode('s-vnum', val=p[1], var=True)

    def p_svnum(self, p):
        '''s-vnum : s-number
                  | s-var'''
        p[0] = p[1]

    def p_sexpr(self, p):
        '''s-expr : SLPAREN s-expr SRPAREN s-conn SLPAREN s-expr SRPAREN
                  | SNOT SLPAREN s-expr SRPAREN
                  | s-expr s-conn s-expr
                  | s-vnum'''
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = AstNode('s-expr', arg1=p[1], oper=p[2], arg2=p[3])
        elif len(p) == 5:
            p[0] = AstNode('s-expr', arg1=p[3], oper=p[1], arg2=None)
        else:
            p[0] = AstNode('s-expr', arg1=p[2], oper=p[4], arg2=p[6])

    def p_sconn(self, p):
        '''s-conn : SOPER
                  | SPRED
                  | SBAR
                  | SAMP
                  | SNOT'''
        p[0] = p[1]

    def p_def(self, p):
        '''def : noun-def
               | name-def
               | verb-def'''
        p[0] = p[1]

    def p_noun_def(self, p):
        '''noun-def : A vterm IS A vterms'''
        p[0] = AstNode('noun-def', name=p[2], bases=p[5])

    def p_terms(self, p):
        '''terms : term COLON terms
                 | term'''
        if len(p) == 4:
            p[0] = p[3] + (p[1],)
        else:
            p[0] = (p[1],)

    def p_name_def(self, p):
        '''name-def : SYMBOL IS A term
                    | QSYMBOL IS A term
                    | vterm IS A vterm'''
        if isinstance(p[1], str):
            p[1] = AstNode('term', val=p[1])
        p[0] = AstNode('name-def', name=p[1], term_type=p[4])

    def p_verb_def(self, p):
        '''verb-def : TO SYMBOL IS TO terms
                    | TO SYMBOL IS TO terms COMMA mod-defs'''
        name = AstNode('term', val=p[2])
        if len(p) == 6:
            p[0] = AstNode('verb-def', name=name, bases=p[5], objs=())
        else:
            p[0] = AstNode('verb-def', name=name, bases=p[5], objs=p[7])

    def p_mod_defs(self, p):
        '''mod-defs : mod-def COMMA mod-defs
                    | mod-def'''
        if len(p) == 4:
            p[0] = p[3] + (p[1],)
        else:
            p[0] = (p[1],)

    def p_mod_def(self, p):
        'mod-def : SYMBOL A term'
        p[0] = AstNode('mod-def', label=p[1], obj_type=p[3])

    def p_error(self, p):
        raise TermsSyntaxError('syntax error: ' + str(p) +
                        ' parsing ' + self.lex.lexer.lexdata)


class AstNode(object):
    def __init__(self, type, **kwargs):
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)


class Compiler(object):

    def __init__(
            self, session, config,
            lex_optimize=False,
            yacc_optimize=True,
            yacc_debug=False):

        self.session = session
        self.config = config
        self.network = Network(session, config)
        self.lexicon = self.network.lexicon

        self.parser = Parser(
            lex_optimize=lex_optimize,
            yacc_optimize=yacc_optimize,
            yacc_debug=yacc_debug)

    def parse(self, s):
        s = '\n'.join([l for l in s.splitlines() if l and not l.startswith('#')])
        module = self.parser.parse(s)
        url = module.url
        headers = module.headers
        known = False
        if url is not None:
            known = True
            try:
                self.session.query(Import).filter_by(url=url).one()
            except NoResultFound:
                known = False
        if not known:
            asts = module.code
            if len(asts) == 1:
                return self.compile(asts[0])
            asts.reverse()
            for ast in asts:
                self.compile(ast)
            if url is not None:  # XXX Save import even if compile throws an exceptin, saving the line it was thrown at?
                headers = '\n'.join(module.headers) if headers is not None else headers
                new = Import(s, url, headers)
                self.session.add(new)
                self.session.commit()
        return 'OK'

    def compile(self, ast):
        if ast.type == 'definition':
            return self.compile_definition(ast.definition)
        elif ast.type == 'rule':
            return self.compile_rule(ast)
        elif ast.type == 'instant-rule':
            return self.compile_instant_rule(ast)
        elif ast.type == 'fact-set':
            return self.compile_factset(ast.facts)
        elif ast.type == 'question':
            return self.compile_question(ast.facts)
        elif ast.type == 'removal':
            return self.compile_removal(ast.facts)
        elif ast.type == 'import':
            return self.compile_import(ast.url)

    def compile_definition(self, definition):
        if definition.type == 'verb-def':
            term = self.compile_verbdef(definition)
        elif definition.type == 'noun-def':
            term = self.compile_noundef(definition)
        elif definition.type == 'name-def':
            term = self.compile_namedef(definition)
        self.session.commit()
        return term

    def _test_previous(self, name):
        try:
            prev = self.lexicon.get_term(name)
        except TermNotFound:
            pass
        else:
            raise DuplicateWord('Word {} already exists, with type {}'.format(
                name, prev.term_type.name))

    def compile_verbdef(self, defn):
        self._test_previous(defn.name.val)
        bases = [self.lexicon.get_term(t.val) for t in defn.bases]
        objs = {o.label: self.lexicon.get_term(o.obj_type.val)
                for o in defn.objs}
        return self.lexicon.add_subterm(defn.name.val, bases, **objs)

    def compile_noundef(self, defn):
        self._test_previous(defn.name.val)
        bases = [self.lexicon.get_term(t.val) for t in defn.bases]
        return self.lexicon.add_subterm(defn.name.val, bases)

    def compile_namedef(self, defn):
        self._test_previous(defn.name.val)
        term_type = self.lexicon.get_term(defn.term_type.val)
        return self.lexicon.add_term(defn.name.val, term_type)

    def _prepare_rule(self, rule):
        condcode = None
        if rule.pycode:
            condcode = CondCode(rule.pycode)
        conds, prems = [], []
        for sen in rule.prems:
            if sen.type == 'fact':
                prem = self.compile_fact(sen)
                prems.append(prem)
            else:
                cond = self.compile_conddef(sen)
                conds.append(cond)
        consecs = []
        for sen in rule.cons:
            con = self.compile_fact(sen)
            consecs.append(con)
        return prems, conds, condcode, consecs

    def compile_rule(self, rule):
        args = self._prepare_rule(rule)
        self.network.add_rule(*args)
        self.session.commit()
        return 'OK'

    def compile_instant_rule(self, rule_ast):
        args = self._prepare_rule(rule_ast)
        rule = self.network.add_rule(*args)
        # remove premnodes & nodes that have no other rules
        for prem in rule.prems:
            if len(prem.node.prems) == 1:
                node = prem.node
                while len(node.parent.children) == 1:
                    node = node.parent
                self.session.delete(node)
        self.session.delete(rule)
        return 'OK'

    def compile_fact(self, fact):
        true = fact.true
        verb = self.compile_vterm(fact.predicate.verb)
        if fact.predicate.subj is None:
            return verb
        subj = self.compile_obj(fact.predicate.subj)
        mods = self.compile_mods(verb, fact.predicate.mods)
        mods['subj'] = subj
        redundant_var = None
        if fact.predvar:
            redundant_var = self.lexicon.make_var(fact.predvar.val)
        return Predicate(true, verb, redundant_var_=redundant_var, **mods)

    def compile_vterm(self, vterm):
        if vterm.type == 'var':
            return self.lexicon.make_var(vterm.val)
        return self.lexicon.get_term(vterm.val)

    def compile_obj(self, obj):
        if obj.type == 'var':
            return self.lexicon.make_var(obj.val)
        elif obj.type == 'term':
            return self.lexicon.get_term(obj.val)
        elif obj.type == 'fact':
            return self.compile_fact(obj)
        elif obj.type == 'number':
            return self.lexicon.make_term(obj.val, self.lexicon.number)
        elif obj.type == 'set':
            return self.compile_set(obj)

    def compile_set(self, ast):
        var = self.lexicon.make_var(ast.var)
        var.set_condition = ast.stmnt
        return var

    def compile_mods(self, verb, ast):
        mods = {}
        for mod in ast:
            label = mod.label
            try:
                otype = tuple(filter(lambda x: x.label == label, verb.object_types))[0]
            except IndexError:
                raise WrongLabel('Error: label %s is unknown for verb %s (in a rule)' % (label, verb.name))
            obj = self.compile_obj(mod.obj)
            if not isa(obj, otype.obj_type):
                raise WrongObjectType('Error: word %s for label %s is not the correct type: '
                                       'it is a %s and should be a %s' %
                                      (obj.name, label, obj.term_type.name, otype.obj_type.name))
            mods[label] = obj
        return mods

    def compile_conddef(self, sen):
        if sen.type == 'name-def':
            name = self.compile_vterm(sen.name)
            term_type = self.compile_vterm(sen.term_type)
            return CondIsa(name, term_type)
        else:
            name = self.compile_vterm(sen.name)
            base = self.compile_vterm(sen.bases[0])
            return CondIs(name, base)

    def compile_factset(self, facts):
        for f in facts:
            pred = self.compile_fact(f)
            self.network.add_fact(pred)
            self.session.commit()
        return 'OK'

    def compile_question(self, sentences):
        matches = []
        if sentences:
            facts, defs = [], []
            for s in sentences:
                if s.type == 'fact':
                    facts.append(s)
                else:
                    defs.append(s)
            q = [self.compile_fact(f) for f in facts]
            matches = self.network.query(*q)
            for defn in defs:
                if defn.type == 'noun-def':
                    if defn.name.type == 'var':
                        terms = self.lexicon.get_terms
                        #  XXX unfinished
                elif defn.type == 'name-def':
                    term = self.compile_namedef(defn)

        if not matches:
            matches = 'false'
        elif not matches[0]:
            matches = 'true'
        return matches

    def compile_removal(self, facts):
        for f in facts:
            pred = self.compile_fact(f)
            self.network.del_fact(pred)
        self.session.commit()
        return 'OK'

    def compile_import(self, url):
        try:
            self.session.query(Import).filter_by(url=url).one()
        except NoResultFound:
            if url.startswith('file://'):
                path = url[7:]
                try:
                    f = open(path, 'r')
                except Exception as e:
                    raise ImportProblems('Problems opening the file: ' + str(e))
                code = f.read()
                f.close()
            elif url.startswith('http'):
                try:
                    resp = urlopen(url)
                except Exception as e:
                    raise ImportProblems('Problems loading the file: ' + str(e))
                code = resp.read().decode('utf8')
                resp.close()
            else:
                raise ImportProblems('Unknown protocol for <%s>' % url)
            self.parse(code)
        return 'OK'


class Runtime(object):

    def __init__(self, compiler):
        self.compiler = compiler

    def count(self, sen):
        resp = self.compiler.parse(sen + '?')
        if resp == 'false':
            return 0
        elif resp == 'true':
            return 1
        return len(resp)
