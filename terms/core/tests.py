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
import re
from configparser import ConfigParser

from terms.core.terms import Base
from terms.core.network import Network
from terms.core.compiler import KnowledgeBase
from terms.core.log import logger
from terms.core.exceptions import Contradiction


CONFIG = '''
[database]
address = sqlite:///:memory:
[time]
mode = normal
'''


def test_terms(): # test generator
    # read contents of terms/
    # feed each content to run_npl
    d = os.path.join(sys.prefix, 'examples')
    files = os.listdir(d)
    kb = None
    config = ConfigParser()
    config.read_string(CONFIG)
    for f in files:
        if f.endswith('.trm'):
            if kb:
                Base.metadata.drop_all(kb.engine)
            kb = KnowledgeBase(config,
                    lex_optimize=False,
                    yacc_optimize=False,
                    yacc_debug=True)
            yield run_terms, kb, os.path.join(d, f)


def run_terms(kb, fname):
    # open file, read lines
    # tell asserions
    # compare return of questions with provided output
    with open(fname) as f:
        resp = kb.no_response
        for sen in f.readlines():
            logger.info(sen)
            sen = sen.strip()
            if resp is not kb.no_response:
                sen = sen.strip('.')
                logger.info('%s match %s' % (sen, resp))
                assert sen == resp or re.compile(sen).match(resp)
                resp = kb.no_response
            elif sen and not sen.startswith('#'):
                resp = kb.process_line(sen)
