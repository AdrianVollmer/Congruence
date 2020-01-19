#  ccli: A command line interface to Confluence
#  Copyright (C) 2020  Adrian Vollmer
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging


FORMAT = (
    '%(levelname).1s %(asctime)-15s '
    + '%(filename)s:%(lineno)d %(message)s'
)


logging.basicConfig(
    filename="ccli.log",
    filemode='w',
    level=logging.DEBUG,
    format=FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
)

log = logging.getLogger(__name__)

# Disable annoying debug messages about charsets (probably from requests)
logger = logging.getLogger('chardet.charsetprober')
logger.setLevel(logging.INFO)
