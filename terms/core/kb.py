import os
import sys
import time
import json
import multiprocessing as mp
from multiprocessing import Process, JoinableQueue, Lock
from multiprocessing.connection import Listener
from threading import Thread

from sqlalchemy.orm.exc import NoResultFound

from terms.core import register_exec_global
from terms.core.terms import Term, Predicate, isa
from terms.core.terms import ExecGlobal, load_exec_globals
from terms.core.compiler import Compiler, Runtime
from terms.core.sa import get_sasession
from terms.core.daemon import Daemon
from terms.core.utils import set_logging

from terms.core.exceptions import TermNotFound, TermsSyntaxError, WrongLabel
from terms.core.exceptions import IllegalLabel, WrongObjectType
from terms.core.exceptions import ImportProblems, DuplicateWord

import logging
logger = logging.getLogger(__name__)


class TermsJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if type(obj) in (Term, Predicate):
            return str(obj)
        else:
            return super(TermsJSONEncoder, self).default(obj)


class Teller(Process):

    def __init__(self, config, session_factory, teller_queue, *args, **kwargs):
        super(Teller, self).__init__(*args, **kwargs)
        self.config = config
        self.session_factory = session_factory
        self.teller_queue = teller_queue
        self.compiler = None

    def run(self):
        for client in iter(self.teller_queue.get, None):
            totell = []
            for msg in iter(client.recv_bytes, b'FINISH-TERMS'):
                totell.append(msg.decode('utf8'))
            totell = '\n'.join(totell)
            session = self.session_factory()
            self.compiler = Compiler(session, self.config)
            register_exec_global(Runtime(self.compiler), name='runtime')
            load_exec_globals(session)
            if totell.startswith('lexicon:'):
                resp = self._from_lexicon(totell)
            elif totell.startswith('compiler:exec_globals:'):
                resp = self._add_execglobal(totell)
            else:
                self.compiler.network.pipe = client
                try:
                    resp = self.compiler.parse(totell)
                except TermNotFound as e:
                    session.rollback()
                    resp = 'Unknown word: ' + e.args[0]
                except TermsSyntaxError as e:
                    session.rollback()
                    resp = 'Terms syntax error: ' + e.args[0]
                except WrongLabel as e:
                    session.rollback()
                    resp = e.args[0]
                except IllegalLabel as e:
                    session.rollback()
                    resp = 'Error: labels cannot contain underscores: %s' % e.args[0]
                except WrongObjectType as e:
                    session.rollback()
                    resp = e.args[0]
                except ImportProblems as e:
                    session.rollback()
                    resp = e.args[0]
                except DuplicateWord:
                    session.rollback()
                    resp = e.args[0]
                self.compiler.network.pipe = None
                resp = json.dumps(resp, cls=TermsJSONEncoder)
            try:
                client.send_bytes(str(resp).encode('utf8'))
            except BrokenPipeError:
                pass
            else:
                client.send_bytes(b'END')
            client.close()
            session.close()  # XXX needed?
            self.compliler = None
            self.teller_queue.task_done()  # abyss
        self.teller_queue.task_done()
        self.teller_queue.close()

    def _from_lexicon(self, totell):
        q = totell.split(':')
        ttype = self.compiler.lexicon.get_term(q[2])
        if q[1] == 'get-words':
            resp = self.compiler.lexicon.get_terms(ttype)
        elif q[1] == 'get-subwords':
            resp = self.compiler.lexicon.get_subterms(ttype)
        elif q[1] == 'get-verb':
            resp = []
            for ot in ttype.object_types:
                isverb = isa(ot.obj_type, self.compiler.lexicon.verb)
                resp.append([ot.label, ot.obj_type.name, isverb])
        return json.dumps(resp, cls=TermsJSONEncoder)

    def _add_execglobal(self, totell):
# XXX put it in terms.core.exec_globals, in all processes
        egs = totell[22:]
        eg = ExecGlobal(egs)
        session = self.session_factory()
        session.add(eg)
        session.commit()
        session.close()


class KnowledgeBase(Daemon):

    def __init__(self, config):
        set_logging(config)
        self.config = config
        self.pidfile = os.path.abspath(config['pidfile'])
        self.time_lock = Lock()
        self.teller_queue = JoinableQueue()
        self.session_factory = get_sasession(self.config)
        session = self.session_factory()

    def run(self):
        if int(self.config['instant_duration']):
            self.clock = Ticker(self.config, self.session_factory(),
                                self.time_lock, self.teller_queue)
            self.clock.start()

        host = self.config['kb_host']
        port = int(self.config['kb_port'])
        nproc = int(self.config['teller_processes'])
        for n in range(nproc):
            teller = Teller(self.config, self.session_factory, self.teller_queue)
            teller.daemon = True
            teller.start()
        self.socket = Listener((host, port))
        while True:
            try:
                client = self.socket.accept()
            except InterruptedError:
                return
            self.time_lock.acquire()
            self.teller_queue.put(client)
            self.time_lock.release()

    def cleanup(self, signum, frame):
        """cleanup tasks"""
        nproc = int(self.config['teller_processes'])
        for n in range(nproc):
            self.teller_queue.put(None)
        self.teller_queue.close()
        try:
            self.clock.ticking = False
        except AttributeError:
            pass
        self.teller_queue.join()
        try:
            self.clock.join()
        except AttributeError:
            pass
        logger.warn('bye from {n}, received signal {p}'.format(n=mp.current_process().name, p=str(signum)))


class Ticker(Thread):

    def __init__(self, config, session, lock, queue, *args, **kwargs):
        super(Ticker, self).__init__(*args, **kwargs)
        self.config = config
        self.session = session
        self.compiler = Compiler(session, config)
        #register_exec_global(self.compiler, name='compiler')
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
