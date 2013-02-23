
import os
import sys
import logging


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        self.logger.log(self.log_level, buf)

    def flush(self):
        for handler in self.logger.handlers:
            handler.flush()


def get_rlogger(config):
    # set up logging
    pname = sys.argv[0]
    logger = logging.getLogger(pname)
    log_file = os.path.abspath(config['logfile'])
    log_dir = os.path.dirname(log_file)
    if not os.path.isfile(log_file):
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        f = open(log_file, 'w')
        f.write('log file for %s\n\n' % pname)
        f.close()
    hdlr = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(getattr(logging, config['loglevel']))
    reader_logger = StreamToLogger(logger)
    return reader_logger
