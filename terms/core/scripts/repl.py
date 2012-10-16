
import sys
import os.path
try:
    import readline
except ImportError:
    pass
from code import InteractiveConsole
from configparser import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.compiler import KnowledgeBase
from terms.core.network import Network
from terms.core.terms import Base


def repl():
    if len(sys.argv) > 1:
        name = sys.argv[1]
    else:
        name = 'test'
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
    if config['dbname'] == ':memory:':
        Base.metadata.create_all(engine)
        Network.initialize(session)
    kb = KnowledgeBase(session, config)
    ic = InteractiveConsole()
    while True:
        line = ic.raw_input(prompt=kb.prompt)
        if line in ('quit', 'exit'):
            session.close()
            sys.exit('bye')
        resp = kb.process_line(line)
        if resp is not kb.no_response:
            print(resp)
