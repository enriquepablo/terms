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
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


term_to_base = Table('term_to_base', Base.metadata,
    Column('term_id', Integer, ForeignKey('terms.id'), primary_key=True),
    Column('base_id', Integer, ForeignKey('terms.id'), primary_key=True)
)


class Term(Base):
    __tablename__ = 'terms'

    id = Column(Integer, Sequence('term_id_seq'), primary_key=True)
    name = Column(String)
    type_id = Column(Integer, ForeignKey('terms.id'))
    term_type = relationship('Term', remote_side=[id],
                         primaryjoin="Term.id==Term.type_id")
    bases = relationship('Term', backref='subwords',
                         secondary=term_to_base,
                         primaryjoin=id==term_to_base.c.term_id,
                         secondaryjoin=id==term_to_base.c.base_id)
    object_types = relationship('ObjectType', backref='verb',
                          primaryjoin='ObjectType.verb_id==Term.id')

    def __init__(self, name, ttype=None, bases=None, objs=None, _bootstrap=False):
        self.name = name
        if not _bootstrap:
            self.term_type = ttype or bases[0].term_type
        self.bases = bases or []
        self.object_types = objs or []


class ObjectType(Base):
    __tablename__ = 'object_types'

    id = Column(Integer, Sequence('object_id_seq'), primary_key=True)
    label = Column(String)
    obj_type_id = Column(Integer, ForeignKey('terms.id'))
    obj_type = relationship(Term, primaryjoin='Term.id==ObjectType.obj_type_id')
    verb_id = Column(Integer, ForeignKey('terms.id'))

    def __init__(self, label, obj_type):
        self.label = label
        self.obj_type = obj_type
