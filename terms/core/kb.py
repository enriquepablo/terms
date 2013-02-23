import os
import sys
import time
from multiprocessing import Pool, Pipe
from multiprocessing.connection import Listener

from terms.core.compiler import Compiler
from terms.core.sa import get_sasession
from terms.core.daemon import Daemon
from terms.core.logger import get_rlogger


compiler = None


def init_tellers(config, session_factory):
    global compiler
    compiler = Compiler(session_factory(), config)


def tell_teller(pipe, totell):
    compiler.network.pipe = pipe
    resp = compiler.compile(totell)
    compiler.network.pipe = None
    pipe.send(resp)
    pipe.send('END')
    pipe.close()


def init_listeners(tellers, socket):
    while True:
        client = socket.accept()
        totell = client.recv()
        conn, tconn = Pipe()
        tellers.appy_async(tell_teller, (tconn, totell))
        while True:
            resp = conn.recv()
            client.send(resp)
            if resp == 'END':
                conn.close()
                client.close()
                break


class KnowledgeBase(Daemon):

    def __init__(self, config):
        self.config = config
        self.pidfile = os.path.abspath(config['pidfile'])

    def run(self):
        reader_logger = get_rlogger(self.config)
        sys.stdout = reader_logger
        sys.stderr = reader_logger
        print(reader_logger.logger.handlers)
        session_factory = get_sasession(self.config)
        self.tellers = Pool(int(self.config['teller_processes']), init_tellers,
                            (self.config, session_factory))
        host = self.config['kb_host']
        port = int(self.config['kb_port'])
        nproc = int(self.config['teller_processes'])
        socket = Listener((host, port))
        self.listeners = Pool(nproc, init_listeners,
                              (self.tellers, socket))
        while True:
            time.sleep(1)
        # XXX tick

    def cleanup(self):
        """cleanup tasks"""
# stop children
# close session
# say bye

    def reload_config(self):
        """ reload configuration"""
