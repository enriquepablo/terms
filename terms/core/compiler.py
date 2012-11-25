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

from terms.core import register
from terms.core.patterns import SYMBOL_PAT, VAR_PAT, NUM_PAT
from terms.core.network import Network, CondIsa, CondIs, CondCode, Finish
from terms.core.terms import isa, Predicate
from terms.core.exceptions import Contradiction

class Lexer(object):

    states = (
            ('pycode', 'exclusive'),
    )

    tokens = (
            'SYMBOL',
            'NUMBER',
            'COMMA',
            'LPAREN',
            'RPAREN',
            'DOT',
            'QMARK',
            'NOT',
            'IS',
            'A',
            'SEMICOLON',
            'VAR',
            'IMPLIES',
            'RM',
            'PYCODE',
            'FINISH',
            'IMPORT',
            'URL',
            'PDB',
    )

    reserved = {
            'is': 'IS',
            'a': 'A',
            'finish': 'FINISH',
            'import': 'IMPORT',
            'pdb': 'PDB',
            }

    t_NUMBER = NUM_PAT
    t_COMMA = r','
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_DOT = r'\.'
    t_QMARK = r'\?'
    t_NOT = r'!'
    t_SEMICOLON = r';'
    t_VAR = VAR_PAT
    t_IMPLIES = r'->'
    t_RM = r'_RM_'
    t_URL = r'<[^>]+>'

    @TOKEN(SYMBOL_PAT)
    def t_SYMBOL(self,t):
        t.type = self.reserved.get(t.value, 'SYMBOL')    # Check for reserved words
        return t

    # Define a rule so we can track line numbers
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # A string containing ignored characters (spaces and tabs)
    t_ignore  = ' \t'

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

    # Any sequence of non-linebreak characters (not ending in ->)
    def t_pycode_PYCODE(self, t):
        r'.+'
        return t

    t_pycode_ignore  = ''

    # Error handling rule
    def t_pycode_INITIAL_error(self,t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    # Build the lexer
    def build(self,**kwargs):
        self.lexer = lex.lex(module=self, **kwargs)
    
    # Test it output
    def test(self,data):
        self.lexer.input(data)
        while True:
             tok = self.lexer.token()
             if not tok: break
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
            start='construct',
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

    def p_construct(self, p):
        '''construct : definition
                     | rule
                     | fact-set
                     | question
                     | removal
                     | import
                     | pdb'''
        p[0] = p[1]

    def p_pdb(self, p):
        '''pdb : PDB DOT'''
        import pdb;pdb.set_trace()

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
                    | fact
                    | FINISH fact'''
        if len(p) == 3:
            p[0] = AstNode('finish', fact=p[2])
        else:
            p[0] = p[1]

    def p_fact(self, p):
        '''fact : LPAREN predicate RPAREN
                | LPAREN NOT predicate RPAREN'''
        if len(p) == 5:
            p[0] = AstNode('fact', predicate=p[3], true=False)
        else:
            p[0] = AstNode('fact', predicate=p[2], true=True)

    def p_predicate(self, p):
        '''predicate : var
                     | verb subject
                     | verb subject COMMA mods'''
        if len(p) == 2:
            p[0] = AstNode('predicate', verb=p[1], subj=None, mods=())
        elif len(p) == 3:
            p[0] = AstNode('predicate', verb=p[1], subj=p[2], mods=())
        else:
            p[0] = AstNode('predicate', verb=p[1], subj=p[2], mods=p[4])

    def p_verb(self, p):
        '''verb : vterm'''
        p[0] = p[1]

    def p_subject(self, p):
        '''subject : vterm'''
        p[0] = p[1]

    def p_vterm(self, p):
        '''vterm : term
                 | var'''
        p[0] = p[1]

    def p_term(self, p):
        '''term : SYMBOL'''
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
                  | number'''
        p[0] = p[1]

    def p_def(self, p):
        '''def : noun-def
               | name-def
               | verb-def'''
        p[0] = p[1]

    def p_noun_def(self, p):
        '''noun-def : A vterm IS A vterm'''
        p[0] = AstNode('noun-def', name=p[2], bases=[p[5]])

    def p_terms(self, p):
        '''terms : term COMMA terms
                 | term'''
        if len(p) == 4:
            p[0] = p[3] + (p[1],)
        else:
            p[0] = (p[1],)

    def p_name_def(self, p):
        '''name-def : SYMBOL IS A term
                    | vterm IS A vterm'''
        if isinstance(p[1], str):
            p[1] = AstNode('term', val=p[1])
        p[0] = AstNode('name-def', name=p[1], term_type=p[4])

    def p_verb_def(self, p):
        '''verb-def : SYMBOL IS terms
                    | SYMBOL IS terms COMMA mod-defs'''
        name = AstNode('term', val=p[1])
        if len(p) == 4:
            p[0] = AstNode('verb-def', name=name, bases=p[3], objs=())
        else:
            p[0] = AstNode('verb-def', name=name, bases=p[3], objs=p[5])

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
        raise Exception('syntax error: ' + str(p) + ' parsing ' + self.lex.lexer.lexdata)


class AstNode(object):
    def __init__(self, type, **kwargs):
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)


class KnowledgeBase(object):

    def __init__(
            self, session, config,
            lex_optimize=False,
            yacc_optimize=True,
            yacc_debug=False):

        self.session = session
        self.config = config
        self.network = Network(session, config)
        self.lexicon = self.network.lexicon

        self._buffer = ''  # for line input
        self.no_response = object()
        self.prompt = '>>> '

        self.parser = Parser(
            lex_optimize=lex_optimize,
            yacc_optimize=yacc_optimize,
            yacc_debug=yacc_debug)

        register(self.count)

    def parse(self, s):
        ast = self.parser.parse(s)
        return self.compile(ast)

    def count(self, sen):
        resp = self.parse(sen + '?')
        if resp == 'false':
            return 0
        elif resp == 'true':
            return 1
        return len(resp)

    def _parse_buff(self):
        return self.parse(self._buffer)

    def reset_state(self):
        self._buffer = ''
        self.prompt = '>>> '

    def format_results(self, res):
        if isinstance(res, str):
            return res
        resps = [', '.join([k + ': ' + str(v) for k, v in r.items()]) \
                for r in res]
        return '; '.join(resps)

    def process_line(self, line):
        self.prompt = '... '
        resp = self.no_response
        if line:
            self._buffer = '\n'.join((self._buffer, line))
            if self._buffer.endswith('.'):
                try:
                    self._parse_buff()
                except Contradiction as e:
                    resp = 'Contradiction: ' + e.args[0]
                self.reset_state()
            elif self._buffer.endswith('?'):
                resp = self._parse_buff()
                resp = self.format_results(resp)
                self.reset_state()
        return resp

    def compile(self, ast):
        if ast.type == 'definition':
            return self.compile_definition(ast.definition)
        elif ast.type == 'rule':
            return self.compile_rule(ast)
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

    def compile_verbdef(self, defn):
        bases = [self.lexicon.get_term(t.val) for t in defn.bases]
        objs = {o.label: self.lexicon.get_term(o.obj_type.val) for o in defn.objs}
        return self.lexicon.add_subterm(defn.name.val, bases, **objs)

    def compile_noundef(self, defn):
        bases = [self.lexicon.get_term(t.val) for t in defn.bases]
        return self.lexicon.add_subterm(defn.name.val, bases)

    def compile_namedef(self, defn):
        term_type = self.lexicon.get_term(defn.term_type.val)
        return self.lexicon.add_term(defn.name.val, term_type)

    def compile_rule(self, rule):
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
        finish, consecs = [], []
        for sen in rule.cons:
            if sen.type == 'finish':
                fin = self.compile_finish(sen)
                finish.append(fin)
            else:
                con = self.compile_fact(sen)
                consecs.append(con)
        self.network.add_rule(prems, conds, condcode, consecs, finish)
        self.session.commit()
        return 'OK'

    def compile_fact(self, fact):
        true = fact.true
        verb = self.compile_vterm(fact.predicate.verb)
        if fact.predicate.subj is None:
            return verb
        subj = self.compile_vterm(fact.predicate.subj)
        mods = self.compile_mods(fact.predicate.mods)
        mods['subj'] = subj
        return Predicate(true, verb, **mods)

    def compile_vterm(self, vterm):
        if vterm.type == 'var':
            return self.lexicon.make_var(vterm.val)
        return self.lexicon.get_term(vterm.val)

    def compile_mods(self, ast):
        mods = {}
        for mod in ast:
            label = mod.label
            if mod.obj.type == 'var':
                obj = self.lexicon.make_var(mod.obj.val)
            elif mod.obj.type == 'term':
                obj = self.lexicon.get_term(mod.obj.val)
            elif mod.obj.type == 'fact':
                obj = self.compile_fact(mod.obj)
            elif mod.obj.type == 'number':
                obj = self.lexicon.make_term(mod.obj.val, self.lexicon.number)
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

    def compile_finish(self, fin):
        fact = self.compile_fact(fin.fact)
        return Finish(fact)

    def compile_factset(self, facts):
        if self.config['time'] != 'none':
            self.network.passtime()
        nows = []
        for f in facts:
            pred = self.compile_fact(f)
            fact = self.network.add_fact(pred)
            if isa(pred, self.lexicon.now):
                nows.append(fact)
        for fact in nows:
            descent = fact.get_descent()
            for ch in descent:
                if isa(ch.pred, self.lexicon.now):
                    self.network.present.add_object_to_fact(ch, self.lexicon.now_term, ('at_', '_term'))
                    ch.factset = 'past'
                    ch.matches = []
        self.session.commit()
        return 'OK'

    def compile_question(self, facts):
        matches = []
        if facts:
            if isinstance(facts, str):
                facts = (facts,)
            q = [self.compile_fact(f) for f in facts]
            matches = self.network.query(*q)
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
        if url.statrswith('file://'):
            path = url[7:]
            f = open(path, 'r')
            resp = f.read()
            f.close()
        elif url.startswith('http://'):
            resp = urlopen(url)
            code = resp.read()
        self._buffer = ''
        for line in code.decode('ascii').splitlines():
            self.process_line(line)
        self.session.commit()
        return 'OK'

