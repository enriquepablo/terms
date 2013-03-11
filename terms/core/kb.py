import os
import sys
import time
import json
import multiprocessing as mp
from multiprocessing import Process, JoinableQueue, Lock
from multiprocessing.connection import Listener
from threading import Thread

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.inspection import inspect

from terms.core.terms import Term, Predicate, isa
from terms.core.compiler import Compiler
from terms.core.sa import get_sasession
from terms.core.schemata import get_data, set_data, get_schema, SchemaNotFound
from terms.core.daemon import Daemon
from terms.core.pluggable import init_environment
from terms.core.logger import get_rlogger


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
        init_environment(config)
        self.session_factory = session_factory
        self.teller_queue = teller_queue
        self.compiler = None

    def run(self):
        for client in iter(self.teller_queue.get, None):
            totell = client.recv_bytes().decode('ascii')
            session = self.session_factory()
            self.compiler = Compiler(session, self.config)
            if totell.startswith('_metadata:'):
                resp = self._get_metadata(totell)
            elif totell.startswith('_data_get:'):
                resp = self._get_data(totell)
            elif totell.startswith('_data_set:'):
                resp = self._set_data(totell)
            elif totell.startswith('_schema_get:'):
                try:
                    resp = self._get_schema(totell)
                except SchemaNotFound:
                    resp = ''
            else:
                self.compiler.network.pipe = client
                resp = self.compiler.parse(totell)
                self.compiler.network.pipe = None
                resp = json.dumps(resp, cls=TermsJSONEncoder)
            client.send_bytes(str(resp).encode('ascii'))
            client.send_bytes(b'END')
            client.close()
            session.close()
            self.compliler = None
            self.teller_queue.task_done()
        self.teller_queue.task_done()
        self.teller_queue.close()

    def _get_metadata(self, totell):
        q = totell.split(':')
        ttype = self.compiler.lexicon.get_term(q[2])
        if q[1] == 'getwords':
            resp = self.compiler.lexicon.get_terms(ttype)
        elif q[1] == 'getsubwords':
            resp = self.compiler.lexicon.get_subterms(ttype)
        elif q[1] == 'getverb':
            resp = []
            for ot in ttype.object_types:
                isverb = isa(ot.obj_type, self.compiler.lexicon.verb)
                resp.append([ot.label, ot.obj_type.name, isverb])
        return json.dumps(resp, cls=TermsJSONEncoder)

    def _get_data(self, totell):
        q = totell.split(':')
        term = self.compiler.lexicon.get_term(q[1])
        data = get_data(term)
        return data.jsonify()

    def _set_data(self, totell):
        q = totell.split(':')
        term = self.compiler.lexicon.get_term(q[1])
        data = json.loads(q[2])
        set_data(term, data)
        return 'OK'

    def _get_schema(self, totell):
        q = totell.split(':')
        term = self.compiler.lexicon.get_term(q[1])
        data = None
        if isa(term, self.compiler.lexicon.noun):
            schema = get_schema(term)
        else:
            schema = get_schema(term.term_type)
            data = schema.get(term.name)
        mapper = inspect(schema)
        jschema = []
        for field_name in mapper.attrs.keys():
            if field_name == '_id':
                continue
            field = {'name': field_name,
                     'id': field_name,
                     'caption': field_name,
                     'type': 'text'}
            if data:
                field['value'] = getattr(data, field_name)
#            typ = mapper.attrs[field_name].type.__name__
#            if typ == 'Text':
#                field['type'] = 'textarea'
#                if data:
#                    field['html'] = getattr(data, field_name)
#            else:
#                field['type'] = 'text'
#                if data:
#                    field['value'] = getattr(data, field_name)
            jschema.append(field)
        jschema = {'html': jschema}
        return json.dumps(jschema)


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
        self.clock.ticking = False
        self.teller_queue.join()
        self.clock.join()
        print('bye from {n}, received signal {p}'.format(n=mp.current_process().name, p=str(signum)))


class Ticker(Thread):

    def __init__(self, config, session, lock, queue, *args, **kwargs):
        super(Ticker, self).__init__(*args, **kwargs)
        self.config = config
        init_environment(config)
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
