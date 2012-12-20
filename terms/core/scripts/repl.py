
import sys
import os.path
try:
    import readline
except ImportError:
    pass
from code import InteractiveConsole

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core.utils import get_config
from terms.core.compiler import KnowledgeBase
from terms.core.network import Network
from terms.core.terms import Base


def repl():
    config = get_config()
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
            if int(config['instant_duration']):
                kb.clock.ticking = False
            sys.exit('bye')
        resp = kb.process_line(line)
        if resp is not kb.no_response:
            print(resp)
