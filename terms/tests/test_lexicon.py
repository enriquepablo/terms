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

from terms.words import word, noun, thing, verb, exists
from terms.terms import Base
from terms.lexicon import Lexicon


# def test_make_noun():
#     kb = Lexicon()
#     person = kb.make_noun('person')
#     man = kb.make_noun('man', person)
# 
#     assert isinstance(person, word)
#     assert isinstance(person, noun)
#     assert issubclass(person, thing)
# 
# 
# def test_make_name():
#     kb = Lexicon()
#     person = kb.make_noun('person')
#     man = kb.make_noun('man', person)
#     john = kb.make_name('john', man)
# 
# 
# def test_make_verb():
#     kb = Lexicon()
#     goes = kb.make_verb('goes')
# 
#     assert isinstance(goes, word)
#     assert isinstance(goes, verb)
#     assert issubclass(goes, exists)
# 
# 
# def test_make_pred():
#     kb = Lexicon()
#     goes = kb.make_verb('goes')
#     pred = kb.make_pred(goes)
# 
#     assert isinstance(pred, word)
#     assert isinstance(pred, exists)
#     assert isinstance(pred, goes)
# 
# 
# def test_make_subverb():
#     kb = Lexicon()
#     tverb = kb.make_subverb('transitive')
# 
#     assert isinstance(tverb, word)
#     assert issubclass(tverb, verb)

import unittest
from sqlalchemy import create_engine


class LexiconTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.lexicon = Lexicon(self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        del self.lexicon
        del self.engine

    def test_lexicon_word(self):
        wrd = self.lexicon.get_word('word')
        assert wrd is word

    def test_lexicon_thing(self):
        thng = self.lexicon.get_word('thing')
        assert thng is thing

    def test_lexicon_noun(self):
        nun = self.lexicon.get_word('noun')
        assert nun is noun

    def test_lexicon_add_noun(self):
        person = self.lexicon.add_word('person', noun)
        prson = self.lexicon.get_word('person')
        assert person is prson, '%s != %s' % (str(person), str(prson))
        assert isinstance(prson, noun)

    def test_lexicon_add_sub_noun(self):
        self.thnoun = self.lexicon.add_subword('thnoun', (noun,))
        tnoun = self.lexicon.get_word('thnoun')
        assert self.thnoun is tnoun
        assert issubclass(tnoun, noun)

    def test_lexicon_add_noun_and_name(self):
        person = self.lexicon.add_word('person', noun)
        john = self.lexicon.add_word('john', person)
        jhn = self.lexicon.get_word('john')
        assert jhn is john
        assert isinstance(john, word)
        assert isinstance(john, thing)
        assert isinstance(john, person)
        assert not issubclass(john, word)

    def test_lexicon_add_sub_thing_and_name(self):
        person = self.lexicon.add_subword('person', (thing,))
        man = self.lexicon.add_subword('man', (person,))
        john = self.lexicon.add_word('john', man)
        jhn = self.lexicon.get_word('john')
        assert jhn is john
        assert isinstance(john, word)
        assert isinstance(john, thing)
        assert isinstance(john, person)
        assert isinstance(john, man)
        assert not issubclass(john, word)

    def test_lexicon_verb(self):
        vrb = self.lexicon.get_word('verb')
        assert vrb is verb

    def test_lexicon_add_verb_no_object(self):
        goes = self.lexicon.add_word('goes', verb)
        ges = self.lexicon.get_word('goes')
        assert goes is ges, '%s != %s' % (str(goes), str(ges))
        assert isinstance(goes, verb)

    def test_lexicon_add_verb_one_object(self):
        person = self.lexicon.add_word('person', noun)
        goes = self.lexicon.add_word('goes', verb, who=person)
        ges = self.lexicon.get_word('goes')
        assert goes is ges, '%s != %s' % (str(goes), str(ges))
        assert isinstance(goes, verb)
        assert issubclass(goes, exists)
        assert goes.objs['who'] is person

    def test_lexicon_add_verb_two_objects(self):
        person = self.lexicon.add_word('person', noun)
        place = self.lexicon.add_word('place', noun)
        goes = self.lexicon.add_word('goes', verb, **{'who': person,
                                                      'to': place})
        ges = self.lexicon.get_word('goes')
        assert goes is ges, '%s != %s' % (str(goes), str(ges))
        assert isinstance(goes, verb)
        assert issubclass(goes, exists)
        assert goes.objs['who'] is person
        assert goes.objs['to'] is place

    def test_lexicon_add_sub_exists_two_objects_inherit(self):
        person = self.lexicon.add_subword('person', thing)
        place = self.lexicon.add_word('place', noun)
        goes = self.lexicon.add_subword('goes', exists,
                                **{'who': person, 'to': place})
        fgoes = self.lexicon.add_subword('goes_fast', goes)
        fges = self.lexicon.get_word('goes_fast')
        assert fgoes is fges, '%s != %s' % (str(fgoes), str(fges))
        assert isinstance(fgoes, verb)
        assert issubclass(fgoes, exists)
        assert issubclass(fgoes, goes)
        assert fgoes.objs['who'] is person
        assert fgoes.objs['to'] is place

    def test_lexicon_add_sub_exists_two_objects_inherit_twice(self):
        person = self.lexicon.add_subword('person', thing)
        place = self.lexicon.add_word('place', noun)
        goes = self.lexicon.add_subword('goes', exists,
                                **{'who': person, 'to': place})
        frgoes = self.lexicon.add_subword('goes_from', goes,
                                **{'from': place})
        fgoes = self.lexicon.add_subword('goes_fast', frgoes)
        fges = self.lexicon.get_word('goes_fast')
        assert fgoes is fges, '%s != %s' % (str(fgoes), str(fges))
        assert isinstance(fgoes, verb)
        assert issubclass(fgoes, exists)
        assert issubclass(fgoes, goes)
        assert fgoes.objs['who'] is person
        assert fgoes.objs['to'] is place
        assert fgoes.objs['from'] is place
