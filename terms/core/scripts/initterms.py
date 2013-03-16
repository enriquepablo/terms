import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core import register_exec_global
from terms.core.utils import get_config
from terms.core.network import Network
from terms.core.compiler import Compiler
from terms.core.terms import Base
from terms.core.schemata import Schema
from terms.core.pluggable import load_plugins, get_plugins


def init_terms():
    config = get_config()
    address = '%s/%s' % (config['dbms'], config['dbname'])
    load_plugins(config)
    engine = create_engine(address)
    Base.metadata.create_all(engine)
    Schema.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    Network.initialize(session)
    session.commit()
    session.close()
    if config['plugins']:
        compiler = Compiler(Session(), config)
        register_exec_global(compiler, name='compiler')
        for m in get_plugins(config):
            dirname = os.path.join(os.path.dirname(m.__file__), 'ontology')
            for f in sorted(os.listdir(dirname)):
                if f.endswith('.trm'):
                    part = os.path.join(dirname, f)
                    compiler.compile_import('file://' + part)
        compiler.session.close()
    sys.exit('Created knowledge store %s' % config['dbname'])
