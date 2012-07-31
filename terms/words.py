# Copyright (c) 2007-2012 by Enrique Pérez Arnaud <enriquepablo@gmail.com>
#
# This file is part of the terms project.
# https://github.com/enriquepablo/terms
#
# The terms project is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The terms project is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with any part of the terms project.
# If not, see <http://www.gnu.org/licenses/>.

class word(type): pass


class noun(word, metaclass=word):
    """ """


class thing(word, metaclass=noun):
    """ """

    def __new__(cls, name):
        """ """
        return super(thing, cls).__new__(cls, name, (), {})

    def __init__(self, name):
        """ """
        return super(thing, self).__init__(name, (), {})


class verb(word, metaclass=word):
    """ """
    def __new__(cls, classname, bases, newdict):
        return super(verb, cls).__new__(cls, classname, bases, {'objs': {}})

    def __init__(self, classname, bases, newdict):
        self.objs = newdict


class exists(word, metaclass=verb):
    """ """

word.bases = ()
word.subtypes = (noun, verb)

noun.bases = (word,)
noun.subtypes = ()

verb.bases = (word,)
verb.subtypes = ()

thing.bases = ()
thing.subtypes = ()

exists.bases = ()
exists.subtypes = ()

def _new_exists(cls, classname, bases, newdict):
    labels = sorted(list(cls.objs))
    name = [cls.__name__]
    for label in labels:
        obj = newdict.get(label, None)
        if obj:
            name.append(label)
            name.append(get_name(obj))

    name = '__'.join(name)
    return super(exists, cls).__new__(cls, name, bases, {})

def _init_exists(self, classname, bases, newdict):
    for label, obj in newdict.items():
        setattr(self, '_' + label, obj)
    if 'true' not in newdict:
        setattr(self, '_true', True)

def _getattr_exists(self, label):
    if label not in ('objs',) and \
        not label.startswith('_'):
        label = '_' + label
    return super(exists, self).__getattribute__(label)

def negate(self):
    true = getattr(self, 'true', True)
    self._true = not true

exists.__new__ = _new_exists
exists.__init__ = _init_exists
exists.__getattribute__ = _getattr_exists
exists.objs = {'subj': word}


def get_name(w):
    return w.__name__

def get_type(w):
    if w is word:
        return w
    return type(w)

def get_bases(w):
    try:
        return w.bases
    except AttributeError:
        bases = []
        _recurse_bases(w, bases)
        w.bases = tuple(bases)
        return w.bases

def _recurse_bases(w, bases):
    for b in w.__bases__:
        if b not in bases and b is not type:
            bases.append(b)
            _recurse_bases(b, bases)


def isa(w1, w2):
    if w1 is word and w2 is word:
        return True
    return isinstance(w1, w2)


def are(w1, w2):
    return issubclass(w1, w2)


class number(int, metaclass=word):
    """ """
