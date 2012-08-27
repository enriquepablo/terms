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

import os
import logging

debug_level = 'INFO'

here = os.path.join(os.path.dirname(__file__))

logger = logging.getLogger('terms')
log_dir = os.path.join(here, 'log')
log_file = os.path.join(log_dir, 'terms.log')
if not os.path.isfile(log_file):
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)
    f = open(log_file, 'w')
    f.write('log file for terms\n\n')
    f.close()
hdlr = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(debug_level)


