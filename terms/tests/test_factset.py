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

import unittest
from sqlalchemy import create_engine

from terms.words import word, noun, verb, thing, exists, get_name, make_pred
from terms.terms import Base
from terms.factset import FactSet
from terms.lexicon import Lexicon
from terms.predicates import Predicate


class LexiconTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.lexicon = Lexicon(self.engine)
        self.person = self.lexicon.add_subword('person', thing)
        self.john = self.lexicon.add_word('john', self.person)
        self.place = self.lexicon.add_subword('place', thing)
        self.madrid = self.lexicon.add_word('madrid', self.place)
        self.goes = self.lexicon.add_subword('goes', exists,
                                    **{'to': self.place})
        self.factset = FactSet(self.lexicon, self.engine)


    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        del self.factset
        del self.lexicon
        del self.engine

    def test_add_fact(self):
        pred = make_pred(self.goes, **{'subject': self.john,
                                       'to': self.madrid})
        tpred = self.factset.add_fact(pred)
        assert get_name(type(pred)) == tpred.verb.name
