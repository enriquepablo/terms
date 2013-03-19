import json

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import String
from sqlalchemy import Column as SAColumn
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

from terms.core.terms import get_bases


class Column(SAColumn):

    def __init__(self,
                 *args,
                 terms_schema_type='text',
                 terms_schema_order='1000',
                 terms_schema_caption='text',
                 terms_schema_help='text',
                 **kwargs):
        super(Column, self).__init__(*args, **kwargs)
        self.terms_schema_type = terms_schema_type
        self.terms_schema_order = terms_schema_order
        self.terms_schema_caption = terms_schema_caption
        self.terms_schema_help = terms_schema_help


class Schema(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    _id = Column(String, primary_key=True)

    def __init__(self, name, **kwargs):
        self._id = name
        self.edit(**kwargs)

    def edit(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def jsonify(self):
        keys = self.__class__.__table__.columns.keys()
        data = {k: getattr(self, k) for k in keys}
        return json.dumps(data)

Schema = declarative_base(cls=Schema)


class SchemaNotFound(Exception):
    pass


def get_schema(noun):
    return _get_schema(noun)


def get_form_schema(noun):
    return _get_schema(noun, sa=False)


def _get_schema(noun, sa=True):
    name = noun.name
    if sa:
        name = name.title()
    schema = globals().get(name, None)
    if schema:
        return schema
    else:
        for n in get_bases(noun):
            name = n.name
            if sa:
                name = name.title()
            if name in globals():
                return globals()[name]
    raise SchemaNotFound(noun.name)


def get_data(kb, name):
    schema = get_schema(name.term_type)
    try:
        return kb.session.query(schema).filter_by(_id=name.name).one()
    except NoResultFound:
        new = schema()
        new._id = name.name
        kb.session.add(new)
        return new


def set_data(kb, name, kwargs):
    data = get_data(kb, name)
    data.edit(**kwargs)
