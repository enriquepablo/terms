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

import datetime

from sqlalchemy import Table, Column, Sequence, Index, DateTime
from sqlalchemy import ForeignKey, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.collections import attribute_mapped_collection

from terms.core.exceptions import WrongLabel


class Base(object):
    pass

Base = declarative_base(cls=Base)


term_to_base = Table('term_to_base', Base.metadata,
    Column('term_id', Integer, ForeignKey('terms.id')),
    Column('base_id', Integer, ForeignKey('terms.id'))
)

term_to_objtype = Table('term_to_objtype', Base.metadata,
    Column('term_id', Integer, ForeignKey('terms.id')),
    Column('objtype_id', Integer, ForeignKey('objecttypes.id'))
)


class Term(Base):
    __tablename__ = 'terms'

    id = Column(Integer, Sequence('term_id_seq'), primary_key=True)
    name = Column(String)
    type_id = Column(Integer, ForeignKey('terms.id'))
    term_type = relationship('Term', remote_side=[id],
                         primaryjoin="Term.id==Term.type_id",
                         post_update=True)
    bases = relationship('Term', backref='subwords',
                         secondary=term_to_base,
                         primaryjoin=id == term_to_base.c.term_id,
                         secondaryjoin=id == term_to_base.c.base_id)
    object_types = relationship('ObjectType',
                         secondary=term_to_objtype,
                         primaryjoin=id == term_to_objtype.c.term_id,
                         secondaryjoin='ObjectType.id==term_to_objtype.c.objtype_id')
    equals = ()
    var = Column(Boolean)
    number = Column(Boolean, default=False)

    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref=backref('vconsecuences', cascade='all'),
                         primaryjoin="Rule.id==Term.rule_id")

    term_name_index = Index('term_name_index', 'name')
    term_type_index = Index('term_type_index', 'type_id')

    # Avoid AttributeErrors
    objects = {}

    def __init__(self, name,
                       ttype=None,
                       bases=None,
                       objs=None,
                       var=False,
                       _bootstrap=False):
        self.name = name
        self.var = var
        self._sup_cache = None
        self._sub_cache = None
        if not _bootstrap:
            self.term_type = ttype or bases[0].term_type
        used = []
        if objs is None:
            objs = {}
        for label, otype in objs.items():
            objtype = ObjectType(label, otype)
            self.object_types.append(objtype)
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

    def __repr__(self):
        return '<Term: %s>' % str(self)

    def copy(self):
        #  immutable
        return self

    def purge_cache(self, lexicon):
        for sub in lexicon.get_subterms(self):
            sub.purge_sup()
        for sup in get_bases(self):
            sup.purge_sub(lexicon)

    def purge_sup(self):
        for sup in get_bases(self):
            sup.purge_sup()
        self._sup_cache = None

    def purge_sub(self, lexicon):
        for sub in lexicon.get_subterms(self):
            if sub is self:
                continue
            sub.purge_sub(lexicon)
        self._sub_cache = None


class ObjectType(Base):
    ''' '''
    __tablename__ = 'objecttypes'

    id = Column(Integer, Sequence('objecttypes_id_seq'), primary_key=True)
    label = Column(String(100))
    obj_type_id = Column(Integer, ForeignKey('terms.id'))
    obj_type = relationship(Term, primaryjoin='Term.id==ObjectType.obj_type_id')

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
    term_type = relationship('Term', primaryjoin="Term.id==Predicate.type_id", lazy='joined')
    rule_id = Column(Integer, ForeignKey('rules.id'))
    rule = relationship('Rule', backref=backref('consecuences', cascade='all'),
                         primaryjoin="Rule.id==Predicate.rule_id")

    # to avoid AttributeErrors when used as a term
    bases = ()
    name = ''
    var = False

    def __init__(self, true, verb_, redundant_var_=None, **objs):
        '''
        verb is a string.
        args is a dict with strings (labels) to ConObjects
        '''
        self.true = true
        self.term_type = verb_
        labels = [ot.label for ot in verb_.object_types]
        for label, o in objs.items():
            if label not in labels:
                raise WrongLabel('Error: label "%s" is wrong for verb "%s"' % (label, verb_.name))
            self.add_object(label, o)
        self.redundant_var = redundant_var_

    def __str__(self):
        p = not self.true and '!' or ''
        p += str(self.term_type)
        p = ['%s %s' % (p, str(self.get_object('subj')))]
        for label in sorted(self.objects):
            if label != 'subj':
                p.append('%s %s' % (label, str(self.get_object(label))))
        return '(%s)' % ', '.join(p)

    def __repr__(self):
        return '<Predicate: %s>' % str(self)

    def add_object(self, label, obj):
        if isinstance(obj, Predicate):
            self.objects[label] = PObject(label, obj)
        else:
            self.objects[label] = TObject(label, obj)

    def get_object(self, label):
        return self.objects[label].value

    def substitute(self, match):
        if self.term_type.var:
            new = Predicate(self.true, match[self.term_type.name])
        else:
            new = Predicate(self.true, self.term_type)
        for o in self.objects.values():
            obj = o.copy()
            if isinstance(o.value, Predicate):
                obj.value = o.value.substitute(match)
            elif o.value.var:
                value = match[o.value.name]
                if isinstance(o, TObject) and isinstance(value, Predicate):
                    obj = PObject(o.label, value)
                else:
                    obj.value = value
                    obj.value.var = False
            new.objects[obj.label] = obj
        return new

    def copy(self):
        new = Predicate(self.true, self.term_type)
        for o in self.objects.values():
            if o is not None:
                new.objects[o.label] = o.copy()
        return new

    def get_vars(self, vars=None):
        if vars is None:
            vars = []
        for o in self.objects:
            if o.value.var:
                vars.append(o.value)
            elif isinstance(o.value, Predicate):
                o.value.get_vars(vars)
        return vars


class Object(Base):
    '''
    objects for Predicates
    '''
    __tablename__ = 'objects'

    id = Column(Integer, Sequence('object_id_seq'), primary_key=True)
    parent_id = Column(Integer, ForeignKey('predicates.id'))
    parent = relationship('Predicate',
                          backref=backref('objects',
                                          collection_class=attribute_mapped_collection('label'),
                                          lazy='joined',
                                          cascade='all,delete-orphan'),
                          primaryjoin="Predicate.id==Object.parent_id")
    label = Column(String(100))

    otype = Column(Integer)
    __mapper_args__ = {'polymorphic_on': otype}

    def __init__(self, label, term):
        self.label = label
        self.value = term

    def copy(self):
        cls = type(self)
        nval = self.value and self.value.copy() or self.value
        return cls(self.label, nval)


class TObject(Object):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': 0}
    term_id = Column(Integer, ForeignKey('terms.id'))
    value = relationship('Term', primaryjoin="Term.id==TObject.term_id", lazy='joined')


class PObject(Object):
    '''
    '''
    __mapper_args__ = {'polymorphic_identity': 1}
    pred_id = Column(Integer, ForeignKey('predicates.id'))
    value = relationship('Predicate', cascade='all', lazy='joined',
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
        get_equals(t1, search=t2)
    except SearchFound:
        return True
    return False

def get_bases(term, search=None):
    cache = getattr(term, '_sup_cache', None)
    if cache is not None:
        if search and search in cache:
            raise SearchFound(search)
        return cache
    bases = _get_desc(term, 'bases', search=search)
    term._sup_cache = bases
    return bases

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
    return tuple(bset)


class Time(Base):
    '''
    '''
    __tablename__ = 'time'
    id = Column(Integer, default=0, primary_key=True)
    now = Column(Integer, default=0)


class Import(Base):
    '''
    '''
    __tablename__ = 'imports'
    id = Column(Integer, Sequence('import_id_seq'), primary_key=True)
    url = Column(String())
    headers = Column(Text())
    code = Column(Text())
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, code, url, headers):
        self.code = code
        self.url = url
        self.headers = headers


class ExecGlobal(Base):
    '''
    '''
    __tablename__ = 'execglobals'
    id = Column(Integer, Sequence('execglobal_id_seq'), primary_key=True)
    code = Column(Text())

    def __init__(self, code):
        self.code = code


def load_exec_globals(session):
    egs = session.query(ExecGlobal).all()
    from terms.core import localdata
    for eg in egs:
        exec(eg.code, localdata.exec_globals)
