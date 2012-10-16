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

from terms.core import register_fun
from terms.core.patterns import SYMBOL_PAT, VAR_PAT, NUM_PAT
from terms.core.network import Network, CondIsa, CondIs, CondCode, Finish
from terms.core.terms import isa
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


class KnowledgeBase(object):

    precedence = (
        ('left', 'COMMA'),
        ('left', 'LPAREN'),
        ('left', 'SEMICOLON'),
        )

    def __init__(
            self, session, config,
            lex_optimize=False,
            yacc_optimize=True,
            yacc_debug=False):

        self.session = session
        self.config = config
        self.network = Network(session, config)
        self.lexicon = self.network.lexicon
        self.lex = Lexer()

        self._buffer = ''  # for line input
        self.no_response = object()
        self.prompt = '>>> '

        self.lex.build(
            optimize=lex_optimize)
        self.tokens = self.lex.tokens

        self.parser = ply.yacc.yacc(
            module=self, 
            start='construct',
            debug=yacc_debug,
            optimize=yacc_optimize)

        register_fun(self.count)

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
        line = line.strip()
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

    def count(self, sen):
        resp = self.parse(sen + '?')
        if resp == 'false':
            return 0
        elif resp == 'true':
            return 1
        return len(resp)

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
        p[0] = p[1]

    def p_fact_set(self, p):
        '''fact-set : fact-list DOT'''
        if self.config['time'] != 'none':
            self.network.passtime()
        nows = []
        for pred in p[1]:
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
        p[0] = 'OK'

    def p_definition(self, p):
        '''definition : def DOT'''
        if p[1].type == 'noun-def':
            term = self.lexicon.add_subterm(p[1].name, p[1].bases)
        elif p[1].type == 'verb-def':
            term = self.lexicon.add_subterm(p[1].name, p[1].bases, **(p[1].objs))
        elif p[1].type == 'name-def':
            term = self.lexicon.add_term(p[1].name, p[1].term_type)
        self.session.add(term)
        self.session.commit()
        p[0] = 'OK'

    def p_question(self, p):
        '''question : sentence-list QMARK'''
        matches = []
        if p[1]:
            matches = self.network.query(*p[1])
        if not matches:
            matches = 'false'
        elif not matches[0]:
            matches = 'true'
        p[0] = matches

    def p_removal(self, p):
        '''removal : RM fact-list DOT'''
        for pred in p[2]:
            self.network.del_fact(pred)
        self.session.commit()
        p[0] = 'OK'

    def p_import(self, p):
        '''import : IMPORT URL DOT'''
        lineno = self.lex.lexer.lineno
        resp = urlopen(p[2][1:-1])
        code = resp.read()
        self._buffer = ''
        for line in code.decode('ascii').splitlines():
            self.process_line(line)
        self.lex.lexer.lineno = lineno + 1
        self.session.commit()
        p[0] = 'OK'

    def p_rule(self, p):
        '''rule : sentence-list IMPLIES sentence-list DOT
                | sentence-list pylines IMPLIES sentence-list DOT'''
        if len(p) == 6:
            code_str = '\n'.join(p[2])
            conds = [CondCode(code_str.strip())]
            cons = p[4]
        else:
            conds = []
            cons = p[3]
        prems = []
        for sen in p[1]:
            if isa(sen, self.lexicon.exists):
                prems.append(sen)
            else:
                if sen.type == 'name-def':
                    if isinstance(sen.name, str):
                        sen.name = self.lexicon.get_term(sen.name)
                    conds.append(CondIsa(sen.name, sen.term_type))
                else:
                    conds.append(CondIs(sen.name, sen.bases[0]))
        finish, consecs = [], []
        for con in cons:
            if isinstance(con, Finish):
                finish.append(con)
            else:
                consecs.append(con)
        self.network.add_rule(prems, conds, consecs, finish)
        self.session.commit()
        p[0] = 'OK'

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
            p[0] = Finish(p[2])
        else:
            p[0] = p[1]

    def p_fact(self, p):
        '''fact : LPAREN predicate RPAREN
                | LPAREN NOT predicate RPAREN'''
        if len(p) == 5:
            p[3].true = False
            p[0] = p[3]
        else:
            p[0] = p[2]

    def p_predicate(self, p):
        '''predicate : var
                     | verb subject
                     | verb subject COMMA mods'''
        if len(p) == 2:
            p[0] = p[1]
        else:
            if len(p) == 3:
                p[0] = self.lexicon.make_pred(True, p[1], subj=p[2])
            else:
                p[0] = self.lexicon.make_pred(True, p[1], subj=p[2], **p[4])
            self.session.add(p[0])

    def p_verb(self, p):
        '''verb : vterm'''
        p[0] = p[1]

    def p_subject(self, p):
        '''subject : vterm'''
        p[0] = p[1]

    def p_vterm(self, p):
        '''vterm : term
                 | var'''
        if isinstance(p[1], str):
            p[0] = self.lexicon.get_term(p[1])
        else:
            p[0] = p[1]

    def p_term(self, p):
        '''term : SYMBOL'''
        p[0] = p[1]

    def p_var(self, p):
        '''var : VAR'''
        p[0] = self.lexicon.make_var(p[1])
        self.session.add(p[0])


    def p_mods(self, p):
        '''mods : mod COMMA mods
                | mod'''
        if len(p) == 4:
            p[1].update(p[3])
        p[0] = p[1]
 
    def p_mod(self, p):
        '''mod : SYMBOL object'''
        p[0] = {p[1]: p[2]}
    
 
    def p_object(self, p):
        '''object : vterm
                  | fact
                  | NUMBER'''
        if isinstance(p[1], str):
            p[0] = self.lexicon.make_term(p[1], self.lexicon.number)
            self.session.add(p[0])
        else:
            p[0] = p[1]

    def p_def(self, p):
        '''def : noun-def
               | name-def
               | verb-def'''
        p[0] = p[1]

    def p_noun_def(self, p):
        '''noun-def : A SYMBOL IS A term
                    | A vterm IS A vterm'''
        if isinstance(p[5], str):
            p[5] = self.lexicon.get_term(p[5])
        p[0] = AstNode(p[2], 'noun-def', bases=[p[5]])

    def p_terms(self, p):
        '''terms : term COMMA terms
                 | term'''
        if len(p) == 4:
            p[0] = p[3] + (self.lexicon.get_term(p[1]),)
        else:
            p[0] = (self.lexicon.get_term(p[1]),)

    def p_name_def(self, p):
        '''name-def : SYMBOL IS A term
                    | vterm IS A vterm'''
        if isinstance(p[4], str):
            p[4] = self.lexicon.get_term(p[4])
        p[0] = AstNode(p[1], 'name-def', term_type=p[4])

    def p_verb_def(self, p):
        '''verb-def : SYMBOL IS terms
                    | SYMBOL IS terms COMMA mod-defs'''
        if len(p) == 4:
            p[0] = AstNode(p[1], 'verb-def', bases=p[3], objs={})
        else:
            p[0] = AstNode(p[1], 'verb-def', bases=p[3], objs=p[5])

    def p_mod_defs(self, p):
        '''mod-defs : mod-def COMMA mod-defs
                    | mod-def'''
        if len(p) == 4:
            p[1].update(p[3])
        p[0] = p[1]

    def p_mod_def(self, p):
        'mod-def : SYMBOL A term'
        p[0] = {p[1]: self.lexicon.get_term(p[3])}

    def p_error(self, p):
        raise Exception('syntax error: ' + str(p))


class AstNode(object):
    def __init__(self, name, type, **kwargs):
        self.name = name
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)
