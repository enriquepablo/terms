
from multiprocessing import Pool, Pipe

from terms.core.sa import get_sasession


compiler = None

def init_tellers(config, session_factory):
    global compiler
    compiler = Compiler(session_factory(), config)

def tell_teller(pipe, totell):
    compiler.network.pipe = pipe
    resp = compiler.compile(totell)
    compiler.network.pipe = None
    pipe.send('END')
    pipe.close()
    return resp

def init_listeners(tellers, socket):
    while True:
        totell = socket.get()
        conn, tconn = Pipe()
        tellers.appy_async(tell_teller, (tconn, totell))
        while True:
            resp = conn.get()
            socket.put(resp)
            if resp == 'END':
                conn.close()
                break


class KnowledgeBase(object):

    def __init__(self, config):
        self.config = config
        session_factory = get_sasession(config)
        self.tellers = Pool(config['teller_processes'], init_tellers,
                            (config, session_factory))

    def run(self):
        socket = None  # XXX
        self.listeners = Pool(config['teller_processes'], init_listeners,
                              (self.tellers, socket))


