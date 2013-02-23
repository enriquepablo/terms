import os
import sys
import time
from multiprocessing import Pool
from multiprocessing.connection import Listener

from terms.core.compiler import Compiler
from terms.core.sa import get_sasession
from terms.core.daemon import Daemon
from terms.core.logger import get_rlogger


def init_listeners(config, session_factory, socket):
    compiler = Compiler(session_factory(), config)
    while True:
        client = socket.accept()
        totell = client.recv_bytes()
        totell = totell.decode()
        compiler.network.pipe = client
        resp = compiler.parse(totell)
        compiler.network.pipe = None
        client.send_bytes(str(resp).encode('ascii'))
        client.send_bytes(b'END')
        client.close()


class KnowledgeBase(Daemon):

    def __init__(self, config):
        self.config = config
        self.pidfile = os.path.abspath(config['pidfile'])

    def run(self):
        reader_logger = get_rlogger(self.config)
        sys.stdout = reader_logger
        sys.stderr = reader_logger
        session_factory = get_sasession(self.config)
        host = self.config['kb_host']
        port = int(self.config['kb_port'])
        nproc = int(self.config['teller_processes'])
        socket = Listener((host, port))
        self.listeners = Pool(nproc, init_listeners,
                              (self.config, session_factory, socket))
        while True:
            time.sleep(10)
        # XXX tick

    def cleanup(self):
        """cleanup tasks"""
# stop children
# close session
# say bye

    def reload_config(self):
        """ reload configuration"""
