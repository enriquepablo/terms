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

class TermsException(Exception):
    pass

class TermRepeated(TermsException):
    pass


class TermNotFound(TermsException):
    pass


class MissingObject(TermsException):
    pass


class Contradiction(TermsException):
    pass


class IllegalLabel(TermsException):
    pass


class WrongLabel(TermsException):
    pass


class Corruption(TermsException):
    pass


class TermsSyntaxError(TermsException):
    pass


class WrongObjectType(TermsException):
    pass

class ImportProblems(TermsException):
    pass

class DuplicateWord(TermsException):
    pass
