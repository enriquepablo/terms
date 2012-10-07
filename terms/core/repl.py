
import sys
import os.path
try:
    import readline
except ImportError:
    pass
from code import InteractiveConsole
from configparser import ConfigParser

from terms.core.compiler import KnowledgeBase


def repl(dbname):
    config = ConfigParser()
    d = os.path.dirname(sys.modules['terms.core'].__file__)
    fname = os.path.join(d, 'etc', 'terms.cfg')
    config.readfp(open(fname))
    config.read([os.path.join('etc', 'terms.cfg'), os.path.expanduser('~/.terms.cfg')])
    if dbname:
        config['db']['dbname'] = dbname
    kb = KnowledgeBase(config)
    ic = InteractiveConsole()
    while True:
#        try:
        line = ic.raw_input(prompt=kb.prompt)
        if line in ('quit', 'exit'):
            sys.exit('bye')
        resp = kb.process_line(line)
#        except Exception as e:
#            kb.reset_state()
#            resp = e.__class__.__name__
#            resp += e.args and ': ' + e.args[0] or ''
        if resp is not kb.no_response:
            print(resp)
