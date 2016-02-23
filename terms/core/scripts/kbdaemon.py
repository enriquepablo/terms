import sys
import os
import time
import signal

from terms.core.kb import KnowledgeBase
from terms.core.utils import get_config


def start(config):
    config['logfile'] = os.path.abspath(config['logfile'])
    kb = KnowledgeBase(config)
    kb.start()


def stop(config):
    # Get the pid from the pidfile
    pidfile = os.path.abspath(config['pidfile'])
    try:
        with open(pidfile, 'r') as pf:
            pid = int(pf.read().strip())
    except IOError:
        pid = None

    if not pid:
        message = "pidfile {0} does not exist. " + \
                "Daemon not running?\n"
        sys.stderr.write(message.format(pidfile))
        return  # not an error in a restart

    # Try killing the daemon process
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as err:
        e = str(err.args)
        if e.find("No such process") > 0:
            if os.path.exists(pidfile):
                os.remove(pidfile)
            else:
                logger.error(str(err.args))
    sys.exit(1)


def main():
    config = get_config(cmd_line=False)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            start(config)
        elif 'stop' == sys.argv[1]:
            stop(config)
        elif 'restart' == sys.argv[1]:
            stop(config)
            start(config)
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
