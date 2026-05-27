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

"""Explorer plugin: browse Confluence spaces and pages as a tree."""

from __future__ import annotations

from typing import Any, cast

import urwid

from congruence.confluence import PageView
from congruence.external import open_doc_in_cli_browser, open_gui_browser
from congruence.interface import make_request
from congruence.logging import log
from congruence.objects import Content, Page, Space
from congruence.views.common import key_action
from congruence.views.treelistbox import CongruenceTreeListBox, CongruenceTreeListBoxEntry

__help__ = """Confluence Explorer

Expand items with the 'toggle collapse' key. They will dynamically retrieve
more content.
"""


class SpaceView(CongruenceTreeListBox):
    def __init__(self, properties: dict | None = None) -> None:
        self.title = "Explorer"
        url = "rest/spacedirectory/1/search"
        params: dict = {"query": "", "type": "global", "status": "current", "startIndex": "0"}
        headers = {"Accept": "application/json"}
        spaces: list[dict] = []
        while True:
            r = make_request(url, params=params, headers=headers)
            j = r.json()
            spaces += j["spaces"]
            if len(spaces) >= j["totalSize"]:
                break
            params["startIndex"] = len(spaces)

        entries: list[dict] = [{s["key"]: ExpandableSpace(s), "children": []} for s in spaces]
        data = {"Space Directory": {"title": "Space Directory"}, "children": entries}
        super().__init__(data, SpaceEntry, help_string=__help__)

    @key_action
    def toggle_collapse(self, size: tuple | None = None) -> None:
        focus = self.focus  # type: ignore[union-attr]
        if focus is None:
            return
        if focus.expanded:  # type: ignore[union-attr]
            urwid.TreeListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "-")
        else:
            obj = focus.get_value()  # type: ignore[union-attr]
            if not getattr(obj, "expanded", True):
                focus.add_children(obj.get_children())  # type: ignore[union-attr]
                obj.expanded = True
            urwid.TreeListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "+")

    @key_action
    def cli_browser(self, size: tuple | None = None) -> None:
        obj = self.focus.get_value()  # type: ignore[union-attr]
        if isinstance(obj, dict):
            return
        obj_id = obj.id
        log.debug(f"Build HTML view for page with id '{obj_id}'")
        r = make_request(f"rest/api/content/{obj_id}?expand=body.storage")
        content = r.json()["body"]["storage"]["value"]
        html = f"<html><head></head><body>{content}</body></html>"
        open_doc_in_cli_browser(html.encode(), self.app)

    @key_action
    def gui_browser(self, size: tuple | None = None) -> None:
        obj = self.focus.get_value()  # type: ignore[union-attr]
        if isinstance(obj, dict):
            return
        if isinstance(obj, Space):
            url = obj.gui_url
        elif isinstance(obj, Content):
            url = obj.webui_url
        else:
            return
        open_gui_browser(url)


class ExpandableSpace(Space):
    """Space that lazily loads its pages on first expansion."""

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.expanded: bool = False

    def get_children(self) -> list[ExpandablePage]:
        self.expanded = True
        log.debug(f"Load descendants of {self.key}...")
        url = f"rest/api/space/{self.key}/content"
        params: dict = {"depth": "root", "expand": "body,version,history.lastUpdated,space"}
        result: list[dict] = []
        while True:
            r = make_request(url, params=params)
            j = r.json()
            result += j["page"]["results"]
            if len(result) >= j["page"]["size"]:
                break
            params["startIndex"] = len(result)
        pages = [ExpandablePage(p) for p in result]
        log.debug(f"Retrieved {len(pages)} items")
        return pages


class SpaceEntry(CongruenceTreeListBoxEntry):
    def __init__(self, node: Any) -> None:
        self.node = node
        super().__init__(self.node)
        self.expanded = bool(self.node.get_value()["children"])
        self.update_expanded_icon()

    def get_next_view(self) -> PageView | None:
        obj = self.get_value()
        try:
            if obj.type in ("page", "blogpost"):
                return PageView(obj)
        except AttributeError:
            pass
        return None

    def search_match(self, search_string: str) -> bool:
        obj = self.get_value()
        if isinstance(obj, dict):
            return bool(search_string in obj.get("title", ""))
        return obj.match(search_string)

    def add_children(self, children: list) -> None:
        for child in children:
            child_id = getattr(child, "key", child.id)
            self.node.get_value()["children"].append({child_id: child, "children": []})
        # Rebuild the child node cache so the tree walker sees the new nodes
        if hasattr(self.node, "_child_keys"):
            self.node._child_keys = None

    def get_display_text(self) -> str:
        obj = self.get_value()
        if isinstance(obj, dict):
            return obj["title"]
        return obj.get_title()


class ExpandablePage(Page):
    """Page that lazily loads its subpages on first expansion."""

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.expanded: bool = False

    def get_children(self) -> list[ExpandablePage]:
        self.expanded = True
        log.debug(f"Load child pages of {self.id}...")
        r = make_request(
            f"rest/api/content/{self.id}/child/page",
            params={"expand": "body,version,history.lastUpdated,space"},
        )
        pages = [ExpandablePage(p) for p in r.json()["results"]]
        log.debug(f"Retrieved {len(pages)} items")
        return pages


PluginView = SpaceView
