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

import sys
import os
from configparser import ConfigParser
import nose

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.terms import Base
from terms.core.network import Network
from terms.core.compiler import KnowledgeBase


CONFIG = '''
[test]
dbms = postgresql://terms:terms@localhost
dbname = test
#dbms = sqlite://
#dbname = :memory:
time = normal
import =
instant_duration = 0
'''


def test_terms():  # test generator
    # read contents of tests/
    # feed each test to run_npl
    d = os.path.dirname(sys.modules['terms.core'].__file__)
    d = os.path.join(d, 'tests')
    files = os.listdir(d)
    config = ConfigParser()
    config.read_string(CONFIG)
    config = config['test']
    for f in files:
        if f.endswith('.test'):
            address = '%s/%s' % (config['dbms'], config['dbname'])
            engine = create_engine(address)
            Session = sessionmaker(bind=engine)
            session = Session()
            Base.metadata.create_all(engine)
            Network.initialize(session)
            kb = KnowledgeBase(session, config,
                               lex_optimize=False,
                               yacc_optimize=False,
                               yacc_debug=True)
            yield run_terms, kb, os.path.join(d, f)
            kb.session.close()
            Base.metadata.drop_all(engine)


def run_terms(kb, fname):
    # open file, read lines
    # tell assertions
    # compare return of questions with provided output
    with open(fname) as f:
        resp = kb.no_response
        for sen in f:
            sen = sen.rstrip()
            if resp is not kb.no_response:
                sen = sen.strip('.')
                pmsg = 'returned "%s" is not "%s" at line %d for query: %s'
                msg = pmsg % (resp, sen,
                              kb.parser.lex.lexer.lineno,
                              kb.parser.lex.lexer.lexdata)
                nose.tools.assert_equals(sen, resp, msg=msg)
                resp = kb.no_response
            elif sen and not sen.startswith('#'):
                resp = kb.process_line(sen)
