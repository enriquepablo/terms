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
import os.path
import sys
import logging
from configparser import ConfigParser
from optparse import OptionParser


class Match(dict):

    def __init__(self, pred, query=None, prem=None):
        self.pred = pred
        self.paths = []
        self.query = query
        self.prem = prem
        self.building = None
        self.orig_path = ()
        self.fact = None
        self.ancestor = None
        super(Match, self).__init__()

    def copy(self):
        new_match = Match(self.pred)
        for k, v in self.items():
            new_match[k] = v
        new_match.prem = self.prem
        new_match.query = self.query
        new_match.paths = self.paths[:]
        if self.building:
            new_match.building = self.building.copy()
            for l, o in self.items():
                if o is self.building:
                    new_match[l] = new_match.building
                    break
        new_match.orig_path = self.orig_path
        new_match.fact = self.fact
        if self.ancestor:
            new_match.ancestor = self.ancestor.copy()
        return new_match

    def merge(self, m):
        new_match = Match(self.pred)
        tot = {}
        tot.update(self)
        tot.update(m)
        for k, v in tot.items():
            if k in self and k in m and self[k] != m[k]:
                return False
            new_match[k] = v
        return new_match


def merge_submatches(submatches):
    final = []
    while submatches:
        final = submatches.pop()
        if not final:
            return final
        elif not final[0]:
            continue
        break
    while submatches:
        sm = submatches.pop()
        if not sm:
            return sm
        elif not sm[0]:
            continue
        new = []
        for n in sm:
            for m in final:
                nm = m.merge(n)
                if nm:
                    new.append(nm)
        final = new
    return final


def get_config(cmd_line=True):
    config = ConfigParser()
    d = os.path.dirname(sys.modules['terms.core'].__file__)
    fname = os.path.join(d, 'etc', 'terms.cfg')
    config.readfp(open(fname))
    config.read([os.path.expanduser('~/.terms.cfg'),
                 os.path.join('etc', 'terms.cfg')])
    name = 'default'
    if cmd_line:
        parser = OptionParser(usage="usage: %prog [options] [name]")
        parser.add_option("-c", "--config", help="path to config file.")
        opt, args = parser.parse_args()
        name = args[0] if args else name
        if opt.config:
            config.read([opt.config])
    return config[name]


def set_logging(config):
    log_level = os.path.abspath(config.get('loglevel', 'WARNING'))
    logging.root.setLevel(getattr(logging, config['loglevel']))
    log_file = os.path.abspath(config['logfile'])
    log_dir = os.path.dirname(log_file)
    if not os.path.isfile(log_file):
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        f = open(log_file, 'w')
        f.write('log file for Terms\n\n')
        f.close()
    hdlr = logging.FileHandler(log_file)
    lformat = '%(asctime)s %(levelname)s [%(name)s:%(funcName)s]: %(message)s'
    hdlr.setFormatter(logging.Formatter(lformat))
    logging.root.addHandler(hdlr)
