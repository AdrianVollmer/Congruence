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

from congruence.views import CongruenceListBox, CongruenceListBoxEntry, app
from congruence.interface import make_api_call, convert_date
from congruence.logging import log
from congruence.confluence import PageView, CommentView

import urwid


class APIView(CongruenceListBox):

    key_map = {
        'm': ("load_more", "Load more objects"),
        'M': ("load_more", "Load much more objects"
              " (five times the regular amount)"),
    }

    def __init__(self, properties={}):
        self.title = "API"
        self.properties = properties
        self.start = 0
        self.entries = []
        super().__init__(self.entries, help_string=__help__)
        self.update()
        self.set_focus(0)

    def keypress(self, size, key):
        log.debug("Keypress in APIView: %s", key)
        if key == 'm':
            self.load_more()
            return
        if key == 'M':
            self.load_much_more()
            return
        if key == 'u':
            self.update()
            return
        return super().keypress(size, key)

    def get_feed_entries(self):
        response = make_api_call(
            "search",
            parameters=self.properties["Parameters"],
        )
        result = [CongruenceAPIEntry(e) for e in response]
        #  result = change_filter(result)
        app.alert('Received %d items' % len(result), 'info')
        self.properties["Parameters"]["start"] += \
            self.properties["Parameters"]["limit"]
        return result

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


class CongruenceAPIEntryLine(urwid.Columns):
    def __init__(self, data):
        self.data = data
        content = self.data['content']
        lastUpdated = content['history']['lastUpdated']
        title = [
            content["type"][0].upper(),
            content["space"]["key"],
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

        key_map = {}
        content = self.data['content']
        if content['type'] in ["page", "blogpost"]:
            key_map["enter"] = PageView
        elif content['type'] == "comment":
            key_map["enter"] = CommentView

        super().__init__(
            self.data,
            CongruenceAPIEntryLine,
            key_map,
        )


PluginView = APIView
