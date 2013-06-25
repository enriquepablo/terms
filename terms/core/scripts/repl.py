
import sys
try:
    import readline
except ImportError:
    pass
from code import InteractiveConsole

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terms.core import register_exec_global
from terms.core.utils import get_config
from terms.core.compiler import Compiler


class TermsRepl(object):

    def __init__(self, config):
        self.config = config
        self._buffer = ''
        self.no_response = object()
        self.prompt = '>> '

        address = '%s/%s' % (config['dbms'], config['dbname'])
        engine = create_engine(address)
        Session = sessionmaker(bind=engine)
        if config['dbname'] == ':memory:':
            from terms.core.terms import Base
            Base.metadata.create_all(engine)
            from terms.core.network import Network
            Network.initialize(Session())
        self.compiler = Compiler(Session(), config)
        register_exec_global(self.compiler, name='compiler')

    def _parse_buff(self):
        return self.compiler.parse(self._buffer)
#        conn = Client((self.config['kb_host'], int(self.config['kb_port'])))
#        conn.send_bytes(self._buffer.encode('ascii'))
#        while True:
#            resp = conn.recv_bytes().decode('ascii')
#            if resp == 'END':
#                conn.close()
#                break
#            resp = self.format_results(resp)
#            print(resp)

    def reset_state(self):
        self._buffer = ''
        self.prompt = '>> '

    def format_results(self, res):
        if isinstance(res, str):
            return res
        resps = [', '.join([k + ': ' + str(v) for k, v in r.items()])
                 for r in res]
        return '; '.join(resps)

    def process_line(self, line):
        self.prompt = '.. '
        resp = self.no_response
        if line:
            self._buffer = '\n'.join((self._buffer, line))
            if self._buffer.endswith(('.', '?')):
                resp = self._parse_buff()
                self.reset_state()
        return resp

    def run(self):
        ic = InteractiveConsole()
        while True:
            line = ic.raw_input(prompt=self.prompt)
            if line in ('quit', 'exit'):
                sys.exit('bye')
            resp = self.process_line(line)
            if resp is not self.no_response:
                print(resp)


def repl():
    config = get_config()
    tr = TermsRepl(config)
    tr.run()
