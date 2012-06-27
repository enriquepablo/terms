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

from terms.words import get_name
from terms.predicates import Predicate, Object


class FactSet(object):
    """
    """

    def __init__(self, lexicon):
        self.session = lexicon.session
        self.lexicon = lexicon

    def add_fact(self, verb, _commit=True, true=True, **objs):
        objects = []
        for objt in verb.object_types:
            obj = objs.get(objt.label, None)
            if obj:
                assert obj.isa(objt.term_type)
                objects.append(obj)
        p = Predicate(verb_term, objects, true)
        self.session.add(p)
        if _commit:
            self.session.commit()
        return p

    def query(self, q):
        pass
