
import sys
import os.path
try:
    import readline
except ImportError:
    pass
from code import InteractiveConsole
from configparser import ConfigParser

from terms.core.compiler import KnowledgeBase


def repl():
    fname = os.path.join(sys.prefix, 'etc', 'terms.cfg')
    f = open(fname, 'r')
    config = ConfigParser()
    config.read_file(f)
    f.close()
    kb = KnowledgeBase(config)
    ic = InteractiveConsole()
    while True:
        try:
            line = ic.raw_input(prompt=kb.prompt)
            if line in ('quit', 'exit'):
                sys.exit('bye')
            resp = kb.process_line(line)
        except Exception as e:
            resp = e.args and e.args[0] or e.__class__.__name__
        if resp is not kb.no_response:
            print(resp)
