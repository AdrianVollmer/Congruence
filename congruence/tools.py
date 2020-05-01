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

from congruence.interface import html_to_text
#  from congruence.logging import log
from congruence.args import config

from difflib import unified_diff
from subprocess import Popen, PIPE


def pipe_through(text, command):
    process = Popen(command,
                    stdin=PIPE,
                    stdout=PIPE,
                    stderr=PIPE,
                    shell=True,
                    )
    process.stdin.write(text.encode())
    (output, err) = process.communicate()
    return output.decode()


def create_diff(v1, v2, fromfile="", tofile="", html=False):
    if html:
        v1 = html_to_text(v1, fix_creation_links=True)
        v2 = html_to_text(v2, fix_creation_links=True)
    #  log.debug(v1)
    generator = unified_diff(
        v1.splitlines(),
        v2.splitlines(),
        fromfile=fromfile,
        tofile=tofile,
        lineterm="",
    )

    diff = '\n'.join(generator)

    if isinstance(config['DiffFilter'], list):
        for f in config["DiffFilter"]:
            diff = pipe_through(diff, f)
    else:
        diff = pipe_through(diff, config['DiffFilter'])

    return diff
