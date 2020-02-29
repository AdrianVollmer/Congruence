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
    * U: User

"""

from congruence.views.listbox import CongruenceListBoxEntry
from congruence.logging import log
from congruence.confluence import CommentContextView, PageView, ContentList


class APIView(ContentList):

    def __init__(self, properties={}):
        self.title = "API"
        super().__init__(EntryClass=CongruenceAPIEntry, help_string=__help__)
        self.params = properties['Parameters']
        self.ka_update()
        if self.entries:
            self.set_focus(0)


class CongruenceAPIEntry(CongruenceListBoxEntry):
    def get_next_view(self):
        log.debug(self.obj.type)
        if self.obj.type in ["page", "blogpost"]:
            return PageView(self.obj)
        elif self.obj.type == "comment":
            parent = self.obj._data['resultParentContainer']
            page_id = parent['displayUrl']
            page_id = page_id.split('=')[-1]
            title = parent['title']
            return CommentContextView(
                page_id,
                title,
                self.obj.id,
            )

    def search_match(self, search_string):
        return self.obj.match(search_string)


PluginView = APIView
