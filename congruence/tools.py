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

from __future__ import annotations

from difflib import unified_diff
from subprocess import PIPE, Popen

from congruence.args import config
from congruence.interface import html_to_text


def pipe_through(text: str, command: str) -> str:
    process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    assert process.stdin is not None
    process.stdin.write(text.encode())
    (output, _) = process.communicate()
    return output.decode()


def create_diff(v1: str, v2: str, fromfile: str = "", tofile: str = "", html: bool = False) -> str:
    if html:
        v1 = html_to_text(v1, fix_creation_links=True)
        v2 = html_to_text(v2, fix_creation_links=True)
    generator = unified_diff(v1.splitlines(), v2.splitlines(), fromfile=fromfile, tofile=tofile, lineterm="")
    diff = "\n".join(generator)

    diff_filter = config.get("DiffFilter")
    if diff_filter is None:
        return diff
    if isinstance(diff_filter, list):
        for f in diff_filter:
            diff = pipe_through(diff, f)
    else:
        diff = pipe_through(diff, diff_filter)
    return diff
