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

import ply.lex as lex
import ply.yacc
from ply.lex import TOKEN

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.patterns import SYMBOL_PAT, VAR_PAT, NUM_PAT
from terms.core.network import Network, CondIsa, CondIs, CondCode
from terms.core.lexicon import Lexicon
from terms.core.terms import isa, are
from terms.core.utils import merge_submatches

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
    )

    reserved = {
            'is': 'IS',
            'a': 'A',
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

#    def t_begin_pycode(self, t):
#        r'<-'
#        t.lexer.code_start = t.lexer.lexpos
#        t.lexer.begin('pycode')
#
#    # Any sequence of non-linebreak characters
#    def t_pycode_PYCODE(self, t):
#        r'.+(?=->)'
#        t.value = t.lexer.lexdata[t.lexer.code_start:t.lexer.lexpos+1]
#        t.lexer.lineno += t.value.count('\n')
#        return t
#
#    def t_pycode_IMPLIES(self, t):
#        r'->'
#        t.lexer.begin('INITIAL')
#        return t
#
#    t_pycode_ignore  = ''

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
             tok = lexer.token()
             if not tok: break
             print(tok)


class KnowledgeBase(object):

    precedence = (
        ('left', 'COMMA'),
        ('left', 'LPAREN'),
        ('left', 'SEMICOLON'),
        )

    def __init__(
            self,
            config,
            lex_optimize=True,
            yacc_optimize=True,
            yacc_debug=False):

        self.engine = create_engine(config['database']['address'])
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.config = config
        self.network = Network(self.session, config)
        self.lexicon = self.network.lexicon
        self.factset = self.network.factset
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
        '''construct : assertion
                     | question
                     | removal'''
        p[0] = p[1]

    def p_assertion(self, p):
        '''assertion : sentence-list DOT
                     | rule DOT'''
        if isinstance(p[1], str):  # rule
            p[0] = p[1]
        else:
            for sen in p[1]:
                if isa(sen, self.lexicon.exists):
                    self.network.add_fact(sen)
                else:
                    if sen.type == 'noun-def':
                        term = self.lexicon.add_subterm(sen.name, sen.bases)
                    elif sen.type == 'verb-def':
                        term = self.lexicon.add_subterm(sen.name, sen.bases, **(sen.objs))
                    elif sen.type == 'name-def':
                        term = self.lexicon.add_term(sen.name, sen.term_type)
                    self.session.add(term)
            p[0] = 'OK'

    def p_question(self, p):
        '''question : sentence-list QMARK'''
        matches = []
        if p[1]:
            matches = self.factset.query(*p[1])
        if not matches:
            matches = 'false'
        elif not matches[0]:
            matches = 'true'
        p[0] = matches

    def p_removal(self, p):
        '''removal : RM sentence-list DOT'''
        for pred in p[2]:
            self.network.del_fact(pred)
        p[0] = 'ok'

    def p_rule(self, p):
        '''rule : sentence-list IMPLIES sentence-list
                | sentence-list pylines IMPLIES sentence-list'''
        if len(p) == 5:
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
        self.network.add_rule(prems, conds, cons)
        p[0] = 'OK'

    def p_pylines(self, p):
        '''pylines : PYCODE pylines
                   | PYCODE'''
        if len(p) == 3:
            p[0] = (p[1],) + p[2]
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
        '''sentence : definition
                    | fact'''
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

    def p_definition(self, p):
        '''definition : noun-def
                      | name-def
                      | verb-def'''
        p[0] = p[1]

    def p_noun_def(self, p):
        '''noun-def : A SYMBOL IS A term
                    | A vterm IS A vterm'''
        if len(p) == 6:
            if isinstance(p[5], str):
                p[5] = self.lexicon.get_term(p[5])
            p[0] = AstNode(p[2], 'noun-def', bases=[p[5]])
        else:
            p[0] = AstNode(p[1], 'noun-def', bases=p[3])

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
