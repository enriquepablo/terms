


class KB(object):

    def __init__(self, connection, name):
        self.conn = connection
        self.name = name
        self.lexicon = None
        self.network = None
        self.factset = None

    def tell_fact(self, fact):
