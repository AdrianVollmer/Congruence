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

"""Generic Confluence API query plugin."""

from __future__ import annotations

from congruence.confluence import CommentContextView, ContentList, PageView
from congruence.logging import log
from congruence.views.listbox import ColumnListBoxEntry

__help__ = """Confluence API

What you see here are objects returned by the API. The type of each object
is indicated by a single letter:

    * P: Page
    * C: Comment
    * B: Blogpost
    * A: Attachment
    * U: User

"""


class APIView(ContentList):
    def __init__(self, properties: dict | None = None) -> None:
        self.title = "API"
        super().__init__(EntryClass=CongruenceAPIEntry, help_string=__help__)
        if properties:
            self.params = properties["Parameters"]
        self.update()
        if self.entries:
            self.set_focus(0)


class CongruenceAPIEntry(ColumnListBoxEntry):
    def get_next_view(self) -> PageView | CommentContextView | None:
        from congruence.objects import ContentWrapper
        obj: ContentWrapper = self.obj  # type: ignore[assignment]
        log.debug(obj.type)
        if obj.type in ("page", "blogpost"):
            return PageView(obj)
        if obj.type == "comment":
            parent = obj._data["resultParentContainer"]
            page_id = parent["displayUrl"].split("=")[-1]
            return CommentContextView(page_id, obj.content, obj.content.id)
        return None

    def search_match(self, search_string: str) -> bool:
        from congruence.objects import ContentWrapper
        obj: ContentWrapper = self.obj  # type: ignore[assignment]
        return obj.match(search_string)


PluginView = APIView
