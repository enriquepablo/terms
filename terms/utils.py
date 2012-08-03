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

from sqlalchemy import Table, Column, Sequence
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from terms import patterns
from terms.terms import Base, Session
from terms.words import word, verb, noun, exists, thing, isa, are
from terms.words import get_name, get_type


class Match(dict):

    def __init__(self, fact, query=None, prem=None):
        self.fact = fact  # word
        self.paths = []
        self.query = query
        self.prem = prem
        super(Match, self).__init__()

    def copy(self):
        new_match = Match(self.fact)
        for k, v in self.items():
            new_match[k] = v
        new_match.prem = self.prem
        new_match.query = self.query
        new_match.paths = self.paths[:]
        return new_match

    def merge(self, m):
        new_match = Match(self.fact)
        for k, v in self.items() + m.items():
            if k in m:
                if self[k] != v:
                    return False
            new_match[k] = v
        return new_match


def merge_submatches(submatches):
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
