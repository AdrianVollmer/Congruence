#  congruence: A command line interface to Confluence
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

from congruence.args import args, LOG_FILE

import logging
from io import StringIO


logging.getLogger().setLevel(logging.DEBUG)

FORMAT = (
    '%(levelname).1s %(asctime)-15s '
    + '%(filename)s:%(lineno)d %(message)s'
)

logFormatter = logging.Formatter(FORMAT)

log_stream = StringIO()
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setFormatter(logFormatter)
stream_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logFormatter)
file_handler.setLevel(logging.DEBUG)

log = logging.getLogger(__name__)

log.addHandler(stream_handler)
if args.log:
    log.addHandler(file_handler)

# Disable annoying debug messages about charsets (probably from requests)
logger = logging.getLogger('chardet.charsetprober')
logger.setLevel(logging.INFO)
