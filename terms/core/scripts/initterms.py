import sys
import os.path
from configparser import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.network import Network


def init_terms():
    name = sys.argv[1]
    config = ConfigParser()
    d = os.path.dirname(sys.modules['terms.core'].__file__)
    fname = os.path.join(d, 'etc', 'terms.cfg')
    config.readfp(open(fname))
    config.read([os.path.join('etc', 'terms.cfg'), os.path.expanduser('~/.terms.cfg')])
    if name in config:
        config = config[name]
    else:
        config = config['default']
        config['dbname'] = name
    address = '%s/%s' % (config['dbms'], config['dbname'])
    engine = create_engine(address)
    Session = sessionmaker(bind=engine)
    session = Session()
    Network.initialize(session)
    session.commit()
    session.close()
    sys.exit('Created knowledge store %s' % name)
