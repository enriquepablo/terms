from sqlalchemy.ext.declarative import declared_attr
from colanderalchemy import Column
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

from terms.core.terms import get_bases


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
        return kb.session.query(schema).filter_by(_id=name).one()
    except NoResultFound:
        new = schema(name)
        kb.session.add(new)
        return new


def set_data(kb, name, **kwargs):
    data = get_data(name)
    data.edit(**kwargs)
