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

__help__ = """Confluence Search

Reading these articles will vastly improve your ability to search
Confluence:

    * https://confluence.atlassian.com/conf615/search-967338147.html
    * https://confluence.atlassian.com/conf615/confluence-search-syntax-967338169.html # noqa
"""

from congruence.views.listbox import CongruenceListBoxEntry
from congruence.confluence import CommentContextView, PageView, ContentList


class APIView(ContentList):
    key_actions = ['search confluence']

    def __init__(self, properties={}):
        super().__init__(EntryClass=SearchResultEntry, help_string=__help__)
        self.title = "Search"
        # TODO filter by space, type, user, date
        # TODO order by
        self.params = {
            'cql': '',
            'start': 0,
            'limit': 20,
            'excerpt': 'highlight',
            'expand': 'content.space,content.history.lastUpdated,'
                      'content.history.previousVersion,space.homepage.history',
            'includeArchivedSpaces': 'false',
            'src': 'next.ui.search',
        }
        self.ka_search_confluence()
        self.redraw()

    def ka_search_confluence(self, size=None):
        self.app.get_input("Search:", self.conf_search)

    def conf_search(self, query):
        self.params['cql'] = f'siteSearch ~ "{query}"'
        self.params['start'] = 0
        self.entries = self.get_entries()
        self.redraw()
        if self.entries:
            self.set_focus(0)


class SearchResultEntry(CongruenceListBoxEntry):
    def get_next_view(self):
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
