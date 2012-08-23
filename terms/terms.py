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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr


class Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'

Base = declarative_base(cls=Base)


term_to_base = Table('term_to_base', Base.metadata,
    Column('term_id', Integer, ForeignKey('terms.id')),
    Column('base_id', Integer, ForeignKey('terms.id'))
)


class Term(Base):

    id = Column(Integer, Sequence('term_id_seq'), primary_key=True)
    name = Column(String)
    type_id = Column(Integer, ForeignKey('terms.id'))
    term_type = relationship('Term', remote_side=[id],
                         primaryjoin="Term.id==Term.type_id",
                         post_update=True)
    bases = relationship('Term', backref='subwords',
                         secondary=term_to_base,
                         primaryjoin=id==term_to_base.c.term_id,
                         secondaryjoin=id==term_to_base.c.base_id)
    equals = ()
    object_types = relationship('ObjectType', backref='verb',
                          primaryjoin='ObjectType.verb_id==Term.id')
    var = Column(Boolean)

    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref='vconsecuences',
                         primaryjoin="Rule.id==Term.rule_id")

    # Avoid AttributeErrors
    objects = ()

    def __init__(self, name,
                       ttype=None,
                       bases=None,
                       objs=None,
                       var=False,
                       _bootstrap=False):
        self.name = name
        self.var = var
        if not _bootstrap:
            self.term_type = ttype or bases[0].term_type
        used = []
        if objs is None:
            objs = {}
        for label, otype in objs.items():
            self.object_types.append(ObjectType(label, otype))
            used.append(label)
        if bases:
            for base in bases:
                self.bases.append(base)
                for objtype in base.object_types:
                    if objtype.label not in used:
                        self.object_types.append(objtype)
                        used.append(objtype.label)

    def __str__(self):
        return self.name


class ObjectType(Base):

    id = Column(Integer, Sequence('object_id_seq'), primary_key=True)
    label = Column(String)
    obj_type_id = Column(Integer, ForeignKey('terms.id'))
    obj_type = relationship(Term, primaryjoin='Term.id==ObjectType.obj_type_id')
    verb_id = Column(Integer, ForeignKey('terms.id'))

    def __init__(self, label, obj_type):
        self.label = label
        self.obj_type = obj_type


class Predicate(Base):
    '''
    Predicates, used for interchange and
    persisted as consecuences.
    '''
    __tablename__ = 'predicates'

    id = Column(Integer, Sequence('predicate_id_seq'), primary_key=True)
    true = Column(Boolean)
    type_id = Column(Integer, ForeignKey('terms.id'))
    term_type = relationship('Term', primaryjoin="Term.id==Predicate.type_id")
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref='consecuences',
                         primaryjoin="Rule.id==Predicate.rule_id")

    # to avoid AttributeErrors
    bases = ()
    name = ''
    var = False


    def __init__(self, true, verb_, **objs):
        '''
        verb is a string.
        args is a dict with strings (labels) to ConObjects
        '''
        self.true = true
        self.term_type = verb_
        for label, o in objs.items():
            if isinstance(o, Predicate):
                self.objects.append(PObject(label, o))
            else:
                self.objects.append(TObject(label, o))

    def get_object(self, label):
        try:
            return self._objects[label]
        except AttributeError:
            self._objects = {}
            for o in self.objects:
                self._objects[o.label] = o.value
            return self._objects[label]

    def substitute(self, match):
        if self.term_type.var:
            self.term_type = match[self.term_type.name]
        for o in self.objects:
            if o.value.var:
                o.value = match[o.value.name]
            elif isinstance(o.value, Predicate):
                o.value.substitute(match)
        return self


class Object(Base):
    '''
    objects for Predicates
    '''
    __tablename__ = 'objects'

    id = Column(Integer, Sequence('object_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('predicates.id'))
    parent = relationship('Predicate', backref='objects',
                         primaryjoin="Predicate.id==Object.parent_id")
    label = Column(String)

    otype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': otype}
    
    def __init__(self, label, term):
        self.label = label
        self.value = term


class TObject(Object):
    '''
    '''
    __tablename__ = 'tobjects'
    __mapper_args__ = {'polymorphic_identity': 0}
    oid = Column(Integer, ForeignKey('objects.id'), primary_key=True)
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term', primaryjoin="Term.id==TObject.term_id")


class PObject(Object):
    '''
    '''
    __tablename__ = 'pobjects'
    __mapper_args__ = {'polymorphic_identity': 1}
    oid = Column(Integer, ForeignKey('objects.id'), primary_key=True)
    pred_id = Column(Integer, ForeignKey('predicates.id'))
    value = relationship('Predicate',
                         primaryjoin="Predicate.id==PObject.pred_id")


def isa(t1, t2):
    try:
        ttype = t1.term_type
    except AttributeError:
        return False
    return are(ttype, t2)


def are(t1, t2):
    if t1 == t2:
        return True
    try:
        equals = get_equals(t1, search=t2)
        for eq in equals:
            get_bases(eq, search=t2)
    except SearchFound:
        return True
    return False

def eq(t1, t2):
    if t1 == t2:
        return True
    try:
        equals = get_equals(t1, search=t2)
    except SearchFound:
        return True
    return False

def get_bases(term, search=None):
    return _get_desc(term, 'bases', search=search)

def get_equals(term, search=None):
    return (term,) + _get_desc(term, 'equals', search=search)

class SearchFound(Exception): pass

def _get_desc(term, desc, search=None, bset=None):
    if not bset:
        bset = set()
    bases = getattr(term, desc, None)
    if bases is None:
        return ()
    for base in bases:
        if search and search == base:
            raise SearchFound(base)
        bset.add(base)
        _get_desc(base, desc, search=search, bset=bset)
        if desc != 'equals':
            for eq in base.equals:
                bset.add(eq)
                get_bases(eq, desc, bset)
    return tuple(bset)
