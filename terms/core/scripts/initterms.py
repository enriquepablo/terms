import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.utils import get_config
from terms.core.network import Network
from terms.core.terms import Base


def init_terms():
    config = get_config()
    address = '%s/%s' % (config['dbms'], config['dbname'])
    if config['plugins']:
        plugins = config['plugins'].strip().split('\n')
        for plugin in plugins:
            __import__(plugin + '.schemata')
    engine = create_engine(address)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    Network.initialize(session)
    session.commit()
    session.close()
    sys.exit('Created knowledge store %s' % config['dbname'])
