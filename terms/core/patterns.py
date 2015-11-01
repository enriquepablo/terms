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

import re

VAR_PAT = r'([A-Z][a-z-]*)([A-Z][a-z-]*)?(\d*)'

varpat = re.compile(VAR_PAT)

SYMBOL_PAT = r'[a-z][a-z-_]*\d*'

sympat = re.compile(SYMBOL_PAT)

NAME_PAT = re.compile(r'^([a-z][a-z-]*[a-z])[1-9]+$')

NUM_PAT = r'(([+]|[-])?([0-9]*)(\.)?([0-9]+)(\.)?)+(j)?((e|E)([0-9]+))?'

numpat = re.compile(NUM_PAT)

QUOTED_SYMBOL_PAT = r'"(""|[^"])*"'

qsym_pat = re.compile(QUOTED_SYMBOL_PAT)
