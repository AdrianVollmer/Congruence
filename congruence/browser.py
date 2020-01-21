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

from congruence.args import config, BASE_URL
from congruence.logging import log

from shlex import split
from subprocess import Popen, PIPE


def open_gui_browser(url):
    if not url.startswith(BASE_URL):
        if url.startswith('/'):
            url = f"{BASE_URL}{url}"
        else:
            url = f"{BASE_URL}/{url}"

    cmd = config["GuiBrowser"]
    if '%s' not in cmd:
        cmd = cmd + " '%s'"
    cmd = cmd % url
    log.info("Executing: `%s`" % cmd)
    process = Popen(split(cmd), stdin=PIPE, stderr=PIPE)
    process.communicate()
