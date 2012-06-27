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

from sqlalchemy import Column, Sequence
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship

from terms.terms import Base, Term


class Predicate(Base):
    __tablename__ = 'predicates'

    id = Column(Integer, Sequence('predicate_id_seq'), primary_key=True)
    true = Column(Boolean)
    verb_id = Column(Integer, ForeignKey('terms.id'))
    verb = relationship(Term, primaryjoin='Term.id==Predicate.verb_id')
    objects = relationship('Object', backref='predicate',
                          primaryjoin='Object.predicate_id==Predicate.id')

    def __init__(self, verb, objs=None, true=True):
        self.true = true
        self.verb = verb
        self.objects = objs or []

    def substitute(self, match):
        raise NotImplementedError


class Object(Base):
    __tablename__ = 'objects'

    id = Column(Integer, Sequence('object_id_seq'), primary_key=True)
    label = Column(String)
    obj_id = Column(Integer, ForeignKey('terms.id'))
    object = relationship(Term, primaryjoin='Term.id==Object.obj_id')
    predicate_id = Column(Integer, ForeignKey('predicates.id'))

    def __init__(self, label, obj):
        self.label = label
        self.object = obj
