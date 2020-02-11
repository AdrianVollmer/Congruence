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
import tempfile

import urwid


def open_doc_in_cli_browser(doc, app):
    """Opens a document in a CLI browser

    :doc: the document as a string
    """

    process = Popen(split(config["CliBrowser"]), stdin=PIPE, stderr=PIPE)
    process.stdin.write(doc)
    process.communicate()
    app.loop.screen.clear()


def open_cli_browser(url, app):
    """Opens an URL in a CLI browser"""

    if not url.startswith(BASE_URL):
        if url.startswith('/'):
            url = f"{BASE_URL}{url}"
        else:
            url = f"{BASE_URL}/{url}"

    cmd = config["CliBrowser"]
    if '%s' not in cmd:
        cmd = cmd + " '%s'"
    cmd = cmd % url
    log.info("Executing: `%s`" % cmd)
    app.loop.screen.stop()
    process = Popen(split(cmd), stdin=PIPE, stderr=PIPE)
    process.communicate()
    app.loop.screen.start()


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


class CliBrowserView(urwid.Terminal):
    """A urwid widget for displaying a CLI browser

    :url: the url to display. If it is -, read from stdin.
    """

    def __init__(self, url):
        cmd = config["CliBrowser"]
        if '%s' not in cmd:
            cmd += " '%s'"
        cmd = cmd % url
        if url == '-':
            cmd = cmd.split(' ')[0]

        super().__init__(cmd)


def get_editor_input(prompt):
    """Open a tempfile with an external editor

    :prompt: Text to be written to the file beforehand
    """

    tfile = tempfile.NamedTemporaryFile('w', delete=False)
    tfile.write(prompt)
    tfile.flush()
    cmd = config["Editor"]
    if '%s' not in cmd:
        cmd += " '%s'"
    cmd = cmd % tfile.name
    log.info("Executing: `%s`" % cmd)
    process = Popen(split(cmd))
    process.communicate()
    with open(tfile.name, 'r') as f:
        content = f.read()
    return content
