import os
import sys
import time
from multiprocessing import Process, JoinableQueue, Lock
from multiprocessing.connection import Listener
from threading import Thread

from sqlalchemy.orm.exc import NoResultFound

from terms.core.terms import Predicate
from terms.core.compiler import Compiler
from terms.core.sa import get_sasession
from terms.core.daemon import Daemon
from terms.core.logger import get_rlogger


class Teller(Process):

    def __init__(self, config, session_factory, teller_queue, *args, **kwargs):
        super(Teller, self).__init__(*args, **kwargs)
        self.config = config
        self.session_factory = session_factory
        self.teller_queue = teller_queue

    def run(self):
        for client in iter(self.teller_queue.get, 'STOP'):
            totell = client.recv_bytes().decode('ascii')
            session = self.session_factory()
            compiler = Compiler(session, self.config)
            compiler.network.pipe = client
            resp = compiler.parse(totell)
            compiler.network.pipe = None
            client.send_bytes(str(resp).encode('ascii'))
            client.send_bytes(b'END')
            client.close()
            session.close()
            self.teller_queue.task_done()


class KnowledgeBase(Daemon):

    def __init__(self, config):
        self.config = config
        self.pidfile = os.path.abspath(config['pidfile'])
        self.time_lock = Lock()
        self.teller_queue = JoinableQueue()

    def run(self):
        reader_logger = get_rlogger(self.config)
        sys.stdout = reader_logger
        sys.stderr = reader_logger
        session_factory = get_sasession(self.config)

        if int(self.config['instant_duration']):
            self.clock = Ticker(self.config, session_factory(),
                                self.time_lock, self.teller_queue)
            self.clock.start()

        host = self.config['kb_host']
        port = int(self.config['kb_port'])
        nproc = int(self.config['teller_processes'])

        for n in range(nproc):
            teller = Teller(self.config, session_factory, self.teller_queue)
            teller.daemon = True
            teller.start()
        socket = Listener((host, port))
        while True:
            client = socket.accept()
            self.time_lock.acquire()
            self.teller_queue.put(client)
            self.time_lock.release()

    def cleanup(self):
        """cleanup tasks"""
        nproc = int(self.config['teller_processes'])
        for n in range(nproc):
            self.teller_queue.put('STOP')
        self.teller_queue.join()
        self.clock.ticking = False
        self.clock.join()
        print('bye.')


class Ticker(Thread):

    def __init__(self, config, session, lock, queue, *args, **kwargs):
        super(Ticker, self).__init__(*args, **kwargs)
        self.config = config
        self.session = session
        self.compiler = Compiler(session, config)
        self.time_lock = lock
        self.teller_queue = queue
        self.ticking = True

    def run(self):
        while self.ticking:
            self.time_lock.acquire()
            self.teller_queue.join()
            pred = Predicate(True, self.compiler.lexicon.vtime,
                             subj=self.compiler.lexicon.now_term)
            try:
                fact = self.compiler.network.present.query_facts(pred,
                                                                 []).one()
            except NoResultFound:
                pass
            else:
                self.session.delete(fact)
                self.session.commit()
            self.compiler.network.passtime()
            pred = Predicate(True, self.compiler.lexicon.vtime,
                             subj=self.compiler.lexicon.now_term)
            self.compiler.network.add_fact(pred)
            self.session.commit()
            self.time_lock.release()
            if self.ticking:
                time.sleep(float(self.config['instant_duration']))
            else:
                self.session.close()
