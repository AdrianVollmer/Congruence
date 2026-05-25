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

import tempfile
from shlex import split
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING

import urwid

from congruence.args import BASE_URL, config
from congruence.logging import log

if TYPE_CHECKING:
    from congruence.app import CongruenceApp


def _normalise_url(url: str) -> str:
    if not url.startswith(BASE_URL):
        if url.startswith("/"):
            return f"{BASE_URL}{url}"
        return f"{BASE_URL}/{url}"
    return url


def open_doc_in_cli_browser(doc: bytes, app: CongruenceApp) -> None:
    """Open an in-memory document in the configured CLI browser."""
    process = Popen(split(config["CliBrowser"]), stdin=PIPE, stderr=PIPE)
    assert process.stdin is not None
    process.stdin.write(doc)
    process.communicate()
    app.loop.screen.clear()


def open_cli_browser(url: str, app: CongruenceApp) -> None:
    """Open a URL in the configured CLI browser."""
    url = _normalise_url(url)
    cmd = config["CliBrowser"]
    if "%s" not in cmd:
        cmd = cmd + " '%s'"
    cmd = cmd % url
    log.info(f"Executing: `{cmd}`")
    app.loop.screen.stop()
    process = Popen(split(cmd), stdin=PIPE, stderr=PIPE)
    process.communicate()
    app.loop.screen.start()


def open_gui_browser(url: str) -> None:
    """Open a URL in the configured GUI browser."""
    url = _normalise_url(url)
    cmd = config["GuiBrowser"]
    if "%s" not in cmd:
        cmd = cmd + " '%s'"
    cmd = cmd % url
    log.info(f"Executing: `{cmd}`")
    process = Popen(split(cmd), stdin=PIPE, stderr=PIPE)
    process.communicate()


class CliBrowserView(urwid.Terminal):
    """A urwid widget embedding a CLI browser.

    Pass '-' as *url* to read from stdin.
    """

    def __init__(self, url: str) -> None:
        cmd = config["CliBrowser"]
        if "%s" not in cmd:
            cmd += " '%s'"
        cmd = cmd % url
        if url == "-":
            cmd = cmd.split(" ")[0]
        super().__init__(cmd)


def get_editor_input(prompt: str = "") -> str:
    """Open a temp-file in the configured editor and return its contents."""
    tfile = tempfile.NamedTemporaryFile("w", delete=False)
    tfile.write(prompt)
    tfile.flush()
    cmd = config["Editor"]
    if "%s" not in cmd:
        cmd += " '%s'"
    cmd = cmd % tfile.name
    log.info(f"Executing: `{cmd}`")
    process = Popen(split(cmd))
    process.communicate()
    with open(tfile.name) as f:
        return f.read()
