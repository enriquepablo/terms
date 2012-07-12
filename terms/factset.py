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

    def add_fact(self, pred, _commit=True):
        verb_ = type(pred)
        verb_name = get_name(verb_)
        verb_term = self.lexicon.get_term(verb_name)
        objects = []
        for label, otype in verb_.objs.items():
            obj = getattr(pred, label, None)
            if obj:
                assert isinstance(obj, otype)
                oname = get_name(obj)
                oterm = self.lexicon.get_term(oname)
                objects.append(Object(label, oterm))
        p = Predicate(verb_term, objects)
        self.session.add(p)
        if _commit:
            self.session.commit()
        return p

    @classmethod
    def make_pred(cls, verb_, **objs):
        name = get_name(verb_)
        obj_list = list(objs.items())
        obj_list = sorted(obj_list, key=lambda x: x[0])
        for label, obj in obj_list:
            name += '__' + label + '__' + get_name(obj)
        return verb_(name, (), objs)


    def query(self, q):
        pass
