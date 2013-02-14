import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.utils import get_config
from terms.core.network import Network
from terms.core.compiler import KnowledgeBase
from terms.core.terms import Base
from terms.core.pluggable import init_environment, get_plugins


def init_terms():
    config = get_config()
    address = '%s/%s' % (config['dbms'], config['dbname'])
    init_environment(config)
    engine = create_engine(address)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    Network.initialize(session)
    session.commit()
    session.close()
    if config['plugins']:
        kb = KnowledgeBase(Session(), config)
        for m in get_plugins(config):
            dirname = os.path.dirname(m.__file__)
            ontology = os.path.join(dirname, 'ontology.trm')
            kb.compile_import('file://' + ontology)
        kb.session.close()
    sys.exit('Created knowledge store %s' % config['dbname'])
