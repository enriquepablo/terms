

class _Word(object):
    def __init__(self, id, type=None, bases=(), args=None):
        self.id = id
        self.type = type
        self.bases = bases
        self.args = args or {}

    def __call__(self, id, *bases, **kwargs):
        new = _Word(id, type=self)
        if not bases:
            if are(self, verb):
                bases = (exists,)
            if are(self, noun):
                bases = (thing,)
        args = {}
        for base in reversed(bases):
            bases += base.bases
            args.update(getattr(base, 'args', {}))
        new.bases = tuple(set(bases))
        if isa(self, verb):
            new.args = args
            new.args.update(kwargs)
        return new

    def __str__(self):
        return self.id

    __repr__ = __str__

    def __equals__(self, w):
        if self.id == w.id:
            return True
        return False


def isa(w1, w2):
    if w1.type == w2 or w2 in w1.type.bases:
        return True
    return False


def are(w1, w2):
    if w1 == w2 or w2 in w1.bases:
        return True
    return False


word = _Word('word')
word.type = word
noun = _Word('noun', type=word, bases=(word,))
verb = _Word('verb', type=word, bases=(word,))
number = _Word('number', type=word)
thing = _Word('thing', type=noun, bases=(word,))
exists = _Word('exists', type=verb, bases=(word,), args={'subject': word})


class fact(object):
    def __init__(self, subject, verb_, **kwargs):
        self.subject = subject
        self.type = verb_
        self.bases = ()
        self.args = kwargs

    def __str__(self):
        args = ['%s %s' % (label, str(w)) for label, w in self.args.items()]
        args = ', '.join(args)
        if args:
            return '(%s %s, %s)' % (str(self.type), str(self.subject), args)
        return '(%s %s)' % (str(self.type), str(self.subject))


# >>> import api
# >>> animal = api.noun('animal')
# >>> person = api.noun('person', animal)
# >>> john = person('john')
# >>> anne = person('anne')
# >>> loves = api.verb('loves', who=person)
# >>> f1 = api.fact(john, loves, who=anne)
# >>> wants = api.verb('wants', what=api.exists)
# >>> f2 = api.fact(anne, wants, what=f1)
# >>> str(f2)
# '(wants anne, what (loves john, who anne))'
# >>> john.type.bases
# (animal, thing, word)
# >>> api.isa(john, api.word)
# True
# >>> api.isa(f1, loves)
# True
# >>> Person1 = person('Person1')
# >>> f2 = api.fact(Person1, wants, what=f1)
# >>> str(f2)
# '(wants Person1, what (loves john, who anne))'


class Brain(object):

    def __init__(self):
        self._config = None
        self._session = None
        self._lexicon = None
        self._factset = None
        self._network = None
        self._compiler = None

    def tell_terms(self, trms):
        return self._compiler.parse(trms)

    def tell_word(self, w):
        pass

    def tell_fact(self, f):
        pass

    def ask_fact(self, f):
        pass

    def get_words(self, type):
        pass

    def get_subwords(self, base):
        pass
