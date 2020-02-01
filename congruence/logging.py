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


FORMAT = (
    '%(levelname).1s %(asctime)-15s '
    + '%(filename)s:%(lineno)d %(message)s'
)


if args.log_level:
    log_level = [
        logging.CRITICAL,
        logging.ERROR,
        logging.WARN,
        logging.INFO,
        logging.DEBUG,
    ][args.log_level]

    logging.basicConfig(
        filename=LOG_FILE,
        filemode='w',
        level=log_level,
        format=FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.basicConfig(
        level=logging.CRITICAL,
        format=FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

log_stream = StringIO()
stream_handler = logging.StreamHandler(log_stream)
logFormatter = logging.Formatter(FORMAT)
stream_handler.setFormatter(logFormatter)
log = logging.getLogger(__name__)
log.addHandler(stream_handler)

# Disable annoying debug messages about charsets (probably from requests)
logger = logging.getLogger('chardet.charsetprober')
logger.setLevel(logging.INFO)
