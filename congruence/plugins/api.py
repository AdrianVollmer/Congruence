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

from congruence.views import ConfluenceMainView, ConfluenceListBox,\
    ConfluenceSimpleListEntry
from congruence.interface import make_api_call, convert_date
from congruence.logging import log
from congruence.confluence import PageView, CommentView


def get_feed_entries(properties):
    """Load feed entries from database"""

    response = make_api_call(
        "search",
        parameters=properties["Parameters"],
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0"},
    )
    result = [ConfluenceAPIEntry(e) for e in response]
    #  result = change_filter(result)
    return result


class APIView(ConfluenceMainView):
    def __init__(self, properties={}):
        def body_builder():
            if not self.entries:
                self.entries = get_feed_entries(self.properties)
            return ConfluenceListBox(self.entries)
        self.properties = properties
        self.properties['start'] = 0
        self.entries = []
        if "DisplayName" in self.properties:
            title = "API: %(DisplayName)s" % self.properties
        else:
            title = "API"
        super().__init__(
            body_builder,
            title,
            help_string=__help__,
        )

    def load_more(self):
        log.info("Load more '%s'..." % self.properties["URL"])
        self.properties["start"] += self.properties["limit"]
        self.entries = get_feed_entries(self.properties)
        #  self.__init__(properties=self.properties)


class ConfluenceAPIEntry(ConfluenceSimpleListEntry):
    def __init__(self, data):
        content = data['content']
        if content['type'] in ["page", "blogpost"]:
            view = PageView(data["url"])
        elif content['type'] == "comment":
            view = CommentView(data["url"], title_text=data["title"])
        else:
            view = None

        lastUpdated = content['history']['lastUpdated']
        name = [
            content["type"][0].upper(),
            content["space"]["key"],
            lastUpdated['by']["displayName"],
            convert_date(lastUpdated["when"]),
            content["title"],
        ]

        super().__init__(name, view)


PluginView = APIView
