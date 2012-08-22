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

import os
import re

from terms.terms import Base
from terms.network import Network
from terms.compiler import KB
from terms.log import here, logger


def test_terms(): # test generator
    # read contents of terms/
    # feed each content to run_npl
    d = os.path.join(here, 'examples')
    files = os.listdir(d)
#    yield run_npl, '/home/eperez/virtualenvs/ircbot/src/nl/nl/npl_tests/lists.npl'
    network = None
    for f in files:
        if f.endswith('.trm'):
            if network:
                Base.metadata.drop_all(network.engine)
            network = Network()
            kb = KB(network,
                    lex_optimize=False,
                    yacc_optimize=False,
                    yacc_debug=True)
            yield run_terms, kb, os.path.join(d, f)


def run_terms(kb, fname):
    # open file, read lines
    # tell asserions
    # compare return of questions with provided output
    with open(fname) as f:
        _nr = object()
        resp, buff = _nr, ''
        for sen in f.readlines():
            logger.info(sen)
            sen = sen.strip()
            if resp is not _nr:
                sen = sen.strip('.')
                logger.info('%s match %s' % (sen, resp))
                assert re.compile(sen).match(resp)
                resp = _nr
            elif sen and not sen.startswith('#'):
                buff += ' ' + sen
                if buff.endswith('.'):
                    logger.info(kb.parse(buff))
                    buff = ''
                elif buff.endswith('?'):
                    resp = format_results(kb.parse(buff))
                    logger.info(resp)
                    buff = ''

def format_results(res):
    if isinstance(res, str):
        return res
    resps = []
    for r in res:
        resp = []
        for k, v in r.items():
            resp.append(k + ': ' + str(v))
        resps.append(', '.join(resp))
    return '; '.join(resps)
