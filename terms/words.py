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

from terms.patterns import varpat

class word(type): pass

def _str(self):
    return get_name(self)

word.__str__ = _str

class noun(word, metaclass=word):
    """ """

noun.__str__ = _str


class thing(word, metaclass=noun):
    """ """

    def __new__(cls, name):
        """ """
        return super(thing, cls).__new__(cls, name, (), {})

    def __init__(self, name):
        """ """
        return super(thing, self).__init__(name, (), {})

thing.__str__ = _str

class verb(word, metaclass=word):
    """ """
    def __new__(cls, classname, bases, newdict):
        return super(verb, cls).__new__(cls, classname, bases, {'_objs': {}})

    def __init__(self, classname, bases, newdict):
        self._objs = newdict

verb.__str__ = _str

class exists(word, metaclass=verb):
    """ """

def _str_exists(self):
    s = get_name(get_type(self))
    s += ' ' + get_name(self.subj)
    if not self.true:
        s = '!' + s
    for label in sorted(dir(self)):
        if not label.startswith('_') and label not in ('true', 'subj'):
            s += ', ' + label + ' ' + str(getattr(self, label))
    return '(' + s + ')'

exists.__str__ = _str_exists

word.__bases = ()
word.__subtypes = (noun, verb)

noun.__bases = (word,)
noun.__subtypes = ()

verb.__bases = (word,)
verb.__subtypes = ()

thing.__bases = ()
thing.__subtypes = ()

exists.__bases = ()
exists.__subtypes = ()

def _new_exists(cls, name, bases, newdict):
    if not name:
        labels = sorted(list(cls._objs))
        name = [cls.__name__]
        for label in labels:
            obj = newdict.get(label, None)
            if obj:
                name.append(label)
                name.append(get_name(obj))
        name = '__'.join(name)
    return super(exists, cls).__new__(cls, name, bases, {})

def _init_exists(self, name, bases, newdict):
    for label, obj in newdict.items():
        setattr(self, label, obj)
    if 'true' not in newdict:
        setattr(self, 'true', True)

exists.__new__ = _new_exists
exists.__init__ = _init_exists
exists._objs = {'subj': word}

def negate(self):
    self.true = not self.true


def get_name(w):
    try:
        return w.__name__
    except AttributeError:
        return str(w)

def get_type(w):
    if w is word:
        return w
    return type(w)

def get_bases(w):
    bases = []
    _recurse_bases(w, bases)
    return tuple(bases)

def _recurse_bases(w, bases):
    for b in w.__bases__:
        if b not in bases and b not in (type, object):
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
