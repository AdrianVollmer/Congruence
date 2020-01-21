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

from congruence.views import CongruenceListBox,\
    CongruenceListBoxEntry
from congruence.interface import make_api_call, convert_date
from congruence.logging import log
from congruence.confluence import PageView, CommentView

import urwid


def get_feed_entries(properties):
    """Load feed entries from database"""

    response = make_api_call(
        "search",
        parameters=properties["Parameters"],
    )
    result = [CongruenceAPIEntry(e) for e in response]
    #  result = change_filter(result)
    return result


class APIView(CongruenceListBox):
    def __init__(self, properties={}, focus=None):
        self.title = "API"
        self.properties = properties
        self.entries = get_feed_entries(self.properties)
        super().__init__(self.entries, help_string=__help__)

    def load_more(self):
        log.info("Load more '%s'..." % self.title_text)
        if 'start' not in self.properties["Parameters"]:
            self.properties["Parameters"]['start'] = 0
        self.properties["Parameters"]["start"] +=\
            self.properties["Parameters"]["limit"]
        self.entries += get_feed_entries(self.properties)
        focus = self.body.get_focus()[1]
        self.__init__(properties=self.properties, focus=focus)


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
