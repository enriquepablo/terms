
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.network import Network
from terms.core.terms import Base


def get_sasession(config):
    address = '%s/%s' % (config['dbms'], config['dbname'])
    engine = create_engine(address)
    Session = sessionmaker(bind=engine)
    if config['dbname'] == ':memory:':
        session = Session()
        Base.metadata.create_all(engine)
        Network.initialize(session)
        session.close()
    return Session
