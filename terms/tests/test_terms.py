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

from terms.words import word, noun, thing, verb, exists, get_name, make_pred


def test_noun():
    assert isinstance(noun, word)
    assert issubclass(noun, word)
    assert get_name(word) == 'word'
    assert get_name(noun) == 'noun'



def test_thing():
    #class person(thing): pass
    person = noun('person', (thing,), {})

    assert isinstance(thing, word)
    assert isinstance(thing, noun)
    assert issubclass(thing, word)
    assert not issubclass(thing, noun)
    assert get_name(thing) == 'thing'

    assert isinstance(person, word)
    assert isinstance(person, noun)
    assert issubclass(person, thing)
    assert issubclass(person, word)
    assert not issubclass(person, noun)
    assert get_name(person) == 'person'


def test_nouns_multiinheritance():
    #class person(thing): pass
    person = noun('person', (thing,), {})
    #class female(thing): pass
    female = noun('female', (thing,), {})
    #class woman(person, female): pass
    woman = noun('woman', (person, female), {})

    assert isinstance(woman, word)
    assert isinstance(woman, noun)
    assert issubclass(woman, word)
    assert issubclass(woman, thing)
    assert issubclass(woman, person)
    assert issubclass(woman, female)
    assert not issubclass(woman, noun)
    assert get_name(woman) == 'woman'


def test_thing_name():
    name = thing('name')

    assert isinstance(name, thing)
    assert not isinstance(name, noun)
    assert isinstance(name, word)
    assert get_name(name) == 'name'
    assert get_name(name) == 'name'


def test_name():
    person = noun('person', (thing,), {})
    john = person('john')

    assert isinstance(john, thing)
    assert isinstance(john, person)
    assert not isinstance(john, noun)
    assert isinstance(john, word)
    assert get_name(john) == 'john'


def test_verb():
    assert isinstance(verb, word)
    assert issubclass(verb, word)
    assert get_name(verb) == 'verb'


def test_verbs():
    #class goes(exists): pass
    goes = verb('goes', (exists,), {})

    assert isinstance(goes, word)
    assert isinstance(goes, verb)
    assert issubclass(goes, exists)
    assert get_name(goes) == 'goes'


def test_verbs_with_args():
    person = noun('person', (thing,), {})
    place = noun('place', (thing,), {})
    goes = verb('goes', (exists,), {'who': person,
                                    'from': place,
                                    'to': place})

    assert isinstance(goes, word)
    assert isinstance(goes, verb)
    assert issubclass(goes, exists)

    assert goes.objs['who'] == person
    assert goes.objs['from'] == place
    assert goes.objs['to'] == place

    assert get_name(goes) == 'goes'


def test_exists():
    pred = exists('pred', (), {})

    assert isinstance(pred, exists)
    assert not isinstance(pred, verb)
    assert isinstance(pred, word)
    assert get_name(exists) == 'exists'


def test_predicate():
    #class goes(exists): pass
    goes = verb('goes', (exists,), {})
    pred = goes('goes1', (), {})

    assert isinstance(pred, exists)
    assert not isinstance(pred, verb)
    assert isinstance(pred, word)


def test_predicate_with_args():
    person = noun('person', (thing,), {})
    place = noun('place', (thing,), {})
    goes = verb('goes', (exists,), {'who': person,
                                    'from': place,
                                    'to': place})
    pred = goes('goes1', (), {'who': person('john')})

    assert isinstance(pred, exists)
    assert not isinstance(pred, verb)
    assert isinstance(pred, word)
    assert get_name(pred.who) == 'john'
    assert get_name(pred) == 'goes__who__john', get_name(pred)


def test_make_predicate():
    #class goes(exists): pass
    goes = verb('goes', (exists,), {})
    pred = make_pred(goes)

    assert isinstance(pred, exists)
    assert not isinstance(pred, verb)
    assert isinstance(pred, word)


def test_make_predicate_with_args():
    person = noun('person', (thing,), {})
    place = noun('place', (thing,), {})
    goes = verb('goes', (exists,), {'who': person,
                                    'from': place,
                                    'to': place})
    pred = make_pred(goes, **{'who': person('john')})

    assert isinstance(pred, exists)
    assert not isinstance(pred, verb)
    assert isinstance(pred, word)
    assert isinstance(pred.who, person)
    assert get_name(pred.who) == 'john'
    assert get_name(pred) == 'goes__who__john', get_name(pred)
