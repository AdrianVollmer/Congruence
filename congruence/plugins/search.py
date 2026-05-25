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

"""Confluence full-text search plugin."""

from __future__ import annotations

from congruence.confluence import CommentContextView, ContentList, PageView
from congruence.views.common import key_action
from congruence.views.listbox import ColumnListBoxEntry

__help__ = """Confluence Search

Reading these articles will vastly improve your ability to search Confluence:

    * https://confluence.atlassian.com/conf615/search-967338147.html
    * https://confluence.atlassian.com/conf615/confluence-search-syntax-967338169.html
"""


class APIView(ContentList):
    def __init__(self, properties: dict | None = None) -> None:
        super().__init__(EntryClass=SearchResultEntry, help_string=__help__)
        self.title = "Search"
        self.params = {
            "cql": "",
            "start": 0,
            "limit": 20,
            "excerpt": "highlight",
            "expand": (
                "content.space,content.history.lastUpdated,"
                "content.history.previousVersion,space.homepage.history"
            ),
            "includeArchivedSpaces": "false",
            "src": "next.ui.search",
        }
        self.search_confluence()
        self.redraw()

    @key_action
    def search_confluence(self, size: tuple | None = None) -> None:
        self.app.get_input("Search:", self._conf_search)

    def _conf_search(self, query: str) -> None:
        if not query:
            self.app.alert("Query empty, aborting", "warning")
            return
        self.params["cql"] = f'siteSearch ~ "{query}"'
        self.params["start"] = 0
        self.entries = self.get_entries()
        self.redraw()
        if self.entries:
            self.set_focus(0)


class SearchResultEntry(ColumnListBoxEntry):
    def get_next_view(self) -> PageView | CommentContextView | None:
        if self.obj.type in ("page", "blogpost"):
            return PageView(self.obj)
        if self.obj.type == "comment":
            parent = self.obj._data["resultParentContainer"]
            page_id = parent["displayUrl"].split("=")[-1]
            return CommentContextView(page_id, self.obj.content, self.obj.content.id)
        return None

    def search_match(self, search_string: str) -> bool:
        return self.obj.match(search_string)


PluginView = APIView
