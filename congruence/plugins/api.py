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

__help__ = """Confluence API

What you see here are objects returned by the API. The type of each object
is indicated by a single letter:

    * P: Page
    * C: Comment
    * B: Blogpost
    * A: Attachment

"""

from congruence.views.listbox import CongruenceListBox, \
    CongruenceListBoxEntry
from congruence.interface import make_api_call, convert_date, make_request
from congruence.logging import log
from congruence.args import config
from congruence.confluence import PageView, CommentView

import re
import json
from subprocess import Popen, PIPE

import urwid


class APIView(CongruenceListBox):

    key_map = {
        'u': ("update", "Update the entire list"),
        'm': ("load more", "Load more objects"),
        'M': ("load much more", "Load much more objects"
              " (five times the regular amount)"),
        'b': ("cli browser", "Open with CLI browser"),
    }

    def __init__(self, properties={}):
        self.title = "API"
        self.properties = properties
        self.start = 0
        self.entries = []
        super().__init__(self.entries, help_string=__help__)
        self.update()
        if self.entries:
            self.set_focus(0)

    def key_action(self, action, size=None):
        if action == "load more":
            self.load_more()
        elif action == "load much more":
            self.load_much_more()
        elif action == "update":
            self.update()
        elif action == "cli browser":
            self.open_cli_browser()
        else:
            super().key_action(action, size=size)

    def get_feed_entries(self):
        response = make_api_call(
            "search",
            parameters=self.properties["Parameters"],
        )
        # TODO wrap data in objects
        # TODO fix encoding
        if response:
            response = [e for e in response if 'content' in e]
            result = [CongruenceAPIEntry(e) for e in response]
            #  result = change_filter(result)
            self.app.alert('Received %d items' % len(result), 'info')
            self.properties["Parameters"]["start"] += \
                self.properties["Parameters"]["limit"]
            return result
        return []

    def load_more(self):
        log.info("Load more ...")
        self.entries += self.get_feed_entries()
        self.redraw()

    def load_much_more(self):
        log.info("Load much more ...")
        p = self.properties
        p["Parameters"]["limit"] *= 5
        self.entries += self.get_feed_entries()
        p["Parameters"]["limit"] //= 5
        self.redraw()

    def update(self):
        log.info("Update ...")
        p = self.properties
        p["Parameters"]["start"] = 0
        self.entries = self.get_feed_entries()
        self.redraw()

    def open_cli_browser(self):
        node = self.get_focus()[0]
        id = node.data['content']['id']
        #  log.debug(data)
        log.debug("Build HTML view for page with id '%s'" % id)
        rest_url = f"rest/api/content/{id}?expand=body.storage"
        content = make_request(rest_url).text
        content = json.loads(content)
        content = content["body"]["storage"]["value"]

        content = f"<html><head></head><body>{content}</body></html>"
        process = Popen(config["CliBrowser"], stdin=PIPE, stderr=PIPE)
        process.stdin.write(content.encode())
        process.communicate()
        self.app.loop.screen.clear()


class CongruenceAPIEntryLine(urwid.Columns):
    def __init__(self, data):
        self.data = data
        content = self.data['content']
        lastUpdated = content['history']['lastUpdated']
        if 'space' in content:
            space = content["space"]["key"]
        else:
            space = "?"
        title = [
            content["type"][0].upper(),
            space,
            lastUpdated['by']["displayName"],
            convert_date(lastUpdated["when"]),
            content["title"],
        ]

        super().__init__(
            [('pack', urwid.Text(t)) for t in title],
            dividechars=1
        )


class CongruenceAPIEntry(CongruenceListBoxEntry):
    def __init__(self, data):
        self.data = data

        super().__init__(
            self.data,
            CongruenceAPIEntryLine,
        )

    def get_next_view(self):
        content = self.data['content']
        if content['type'] in ["page", "blogpost"]:
            return PageView(self.data)
        elif content['type'] == "comment":
            return CommentView(self.data)

    def get_details_view(self):
        return CongruenceListBox(urwid.SimpleFocusListWalker([urwid.Text(
            json.dumps(self.data, indent=2, sort_keys=True)
        )]))

    def search_match(self, search_string):
        return re.match(
            search_string,
            self.data['content']['title']
        )


PluginView = APIView
