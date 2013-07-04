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

from threading import local

localdata = local()

localdata.exec_globals = {'__builtins__': __builtins__}


def register_exec_global(fun, name=''):
    if name:
        localdata.exec_globals[name] = fun
    else:
        try:
            localdata.exec_globals[fun.__name__] = fun
        except AttributeError:  # method?
            localdata.exec_globals[fun.__func__.__name__] = fun


def count(compiler, sen):
    resp = compiler.parse(sen + '?')
    if resp == 'false':
        return 0
    elif resp == 'true':
        return 1
    return len(resp)

register_exec_global(count)
