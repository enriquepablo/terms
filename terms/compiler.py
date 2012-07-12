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

from terms.patterns import TERM_PAT, VAR_PAT

class Lexer(object):

    tokens = (
            'SYMBOL',
            'COMMA',
            'LPAREN',
            'RPAREN',
            'DOT',
            'NOT',
            'IS',
            'A',
    )

    reserved = {
            'is': 'IS',
            'a': 'A',
            }

    t_COMMA = r','
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_DOT = r'\.'
    t_NOT = r'!'

    @TOKEN(SYMBOL_PAT)
    def t_SYMBOL(self,t):
        t.type = self.reserved.get(t.value, 'SYMBOL')    # Check for reserved words
        return t

    # Define a rule so we can track line numbers
    def t_newline(self,t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # A string containing ignored characters (spaces and tabs)
    t_ignore  = ' \t'

    # Error handling rule
    def t_error(self,t):
        print "Illegal character '%s'" % t.value[0]
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
             print tok


class KB(object):

    def __init__(
            self,
            network,
            lex_optimize=True,
            yacc_optimize=True,
            yacc_debug=False):

        self.network = network
        self.lexicon = network.lexicon
        self.factset = network.factset
        self.lex = Lexer()

        self.lex.build(
            optimize=lex_optimize)
        self.tokens = self.lex.tokens

        self.parser = ply.yacc.yacc(
            module=self, 
            start='sentence',
            debug=yacc_debug,
            optimize=yacc_optimize,
            tabmodule=yacctab)

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
        self.lex.reset_lineno()
        return self.parser.parse(text, lexer=self.lex, debug=debuglevel)

    # BNF

    def p_sentence(self, p):
        '''sentence : assertion'''
        p[0] = p[1]

    def p_assertion(self, p):
        '''assertion : definition DOT
                     | fact DOT'''
        if isa(p[1], exists):
            p[0] = self.network.add_fact(p[1])
        else:
            p[0] = self.lexicon.save_word(p[1])

    def p_fact(self, p):
        '''fact : LPAREN predicate RPAREN
                | LPAREN NOT predicate RPAREN'''
        if len(p) == 5:
            pred = p[3]
            pred.negate()
            p[0] = pred
        else:
            p[0] = p[2]

    def p_predicate(self, p):
        '''predicate : verb subject
                     | verb subject COMMA mods'''
        if len(p) == 4:
            p[0] = self.factset.make_pred(p[1], subj=p[2])
        else:
            p[0] = self.factset.make_pred(p[1], subj=p[2], **p[4])

    def p_verb(self, p):
        '''verb : term'''
        p[0] = p[1]


    def p_subject(self, p):
        '''subject : term'''
        p[0] = p[1]

    def p_term(self, p):
        '''term : SYMBOL'''
        p[0] = self.lexicon.get_word(p[1])

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
        '''object : term
                  | fact'''
        p[0] = p[1]

    def p_definition(self, p):
        '''definition : noun-def
                      | name-def
                      | verb-def'''
        p[0] = p[1]

    def p_noun_def(self, p):
        'noun-def : SYMBOL IS terms'
        p[0] = self.lexicon.make_subword(p[1], p[3])

 
    def p_terms(self, p):
        '''terms : term COMMA terms
                 | term'''
        if len(p) == 4:
            p[0] = p[3] + (p[1],)
        else:
            p[0] = (p[1],)

    def p_name_def(self, p):
        '''name-def : SYMBOL IS A term'''
        p[0] = self.lexicon.make_word(p[1], p[3])

    def p_verb_def(self, p):
        '''verb-def :  SYMBOL IS terms COMMA mod-defs'''
        p[0] = self.lexicon.make_subword(p[1], p[3], **p[5])

    def p_mod_defs(self, p):
        '''mod-defs : mod-def COMMA mod-defs
                   | mod-def'''
        if len(p) == 4:
            p[1].update(p[3])
        p[0] = p[1]

    def p_mod_def(self, p):
        'mod-def : SYMBOL A term'
        p[0] = {p[1]: p[3]}

