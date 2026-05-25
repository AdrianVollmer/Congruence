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

"""Views and functions specific to Confluence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import congruence.strings as cs
from congruence.external import open_doc_in_cli_browser, open_gui_browser
from congruence.interface import convert_date, make_request
from congruence.logging import log
from congruence.objects import Comment, ContentWrapper
from congruence.tools import create_diff
from congruence.views.common import CongruenceTextBox, key_action
from congruence.views.listbox import ColumnListBoxEntry, CongruenceListBox
from congruence.views.treelistbox import CongruenceCardTreeWidget, CongruenceTreeListBox

if TYPE_CHECKING:
    pass


def _find_child_by_id(children: list[dict], cid: str) -> dict | None:
    """Return the child dict whose top-level key matches *cid*."""
    for child in children:
        if cid in child:
            return child
    return None


def get_comments_of_page(page_id: str) -> list[dict]:
    """Retrieve the comment tree of *page_id* from the Confluence API."""
    log.debug(f"Get comment tree of page {page_id}")

    url = f"rest/api/content/{page_id}/child/comment"
    params: dict[str, Any] = {
        "expand": "body.view,content,history.lastUpdated,version,ancestors,extensions.inlineProperties,version",
        "depth": "all",
        "limit": 9999,
    }

    items: list[dict] = []
    while True:
        r = make_request(url, params=params)
        parsed = r.json()
        items += parsed["results"]
        links = parsed["_links"]
        if "next" in links:
            url = links["next"]
        else:
            break

    result: list[dict] = []
    # Confluence returns a flat list where each item carries its ancestor chain.
    # Reconstruct the nested tree structure.
    for c in items:
        parent = result
        for ancestor in reversed(c["ancestors"]):
            node = _find_child_by_id(parent, ancestor["id"])
            if node is None:
                break
            parent = node["children"]

        parent.append({c["id"]: Comment(c), "children": []})

    return result


class CommentContextView(CongruenceTreeListBox):
    """Display a comment tree anchored to a page."""

    def __init__(self, page_id: str, obj: Any, focus_id: str | None = None) -> None:
        self.title = "Comments"
        log.debug(f"Build CommentContextView for comments of page with id '{page_id}'")
        comments = {
            "0": {"title": obj.title, "id": obj.id},
            "children": get_comments_of_page(page_id),
        }
        help_string = cs.COMMENT_CONTEXT_VIEW_HELP
        super().__init__(comments, CommentWidget, help_string=help_string)
        if not focus_id:
            return
        node = self._body.focus
        while True:
            node = self._body.get_next(node)[1]
            if not node:
                break
            if next(iter(node.get_value().keys())) == focus_id:
                break
        if node:
            self.set_focus(node)

    @key_action
    def reply(self, size: tuple | None = None) -> None:
        obj = self.get_focus()[0].get_value()
        prev_msg = obj.get_content()
        prev_msg = "\n".join(f"## > {line}" for line in prev_msg.splitlines())
        prev_msg = f"## {obj.versionby.display_name} wrote:\n{prev_msg}"
        help_text = cs.REPLY_MSG + prev_msg
        reply = self.app.get_long_input(help_text)

        if reply:
            if obj.send_reply(reply):
                self.app.alert("Comment sent", "info")
            else:
                self.app.alert("Comment failed", "error")
        else:
            self.app.alert("Reply empty, aborting", "warning")

    @key_action
    def like(self, size: tuple | None = None) -> None:
        comment = self.get_focus()[0].get_value()
        if comment.toggle_like():
            if comment.liked:
                self.app.alert("You liked this", "info")
            else:
                self.app.alert("You unliked this", "info")

    @key_action
    def cli_browser(self, size: tuple | None = None) -> None:
        obj = self.focus.get_value()
        try:
            obj_id = obj.id
        except AttributeError:
            obj_id = obj["id"]
        open_content_in_cli_browser(self.app, obj_id)

    @key_action
    def gui_browser(self, size: tuple | None = None) -> None:
        obj = self.focus.get_value()
        open_gui_browser(obj.url)


class SingleCommentView(CongruenceTextBox):
    """Text box showing metadata and content for a single comment."""

    def __init__(self, obj: Comment) -> None:
        self.obj = obj
        self.title = "Comment"
        try:
            update = self.obj._data["version"]
            infos = {
                "Title": obj.get_title(),
                "Last updated by": update["by"]["displayName"],
                "Last updated at": convert_date(update["when"]),
                "Last change message": update["message"],
                "Version number": update["number"],
            }
            text = "\n".join(f"{k}: {v}" for k, v in infos.items())
            text += "\n\n" + self.obj.get_content()
        except KeyError as e:
            self.app.alert(f"KeyError ({e}), displaying raw data", "error")
            text = obj.get_json()
        help_string = cs.COMMENT_VIEW_HELP
        super().__init__(text, help_string=help_string)


class CommentWidget(CongruenceCardTreeWidget):
    def __init__(self, node: Any) -> None:
        self.obj = next(iter(node.get_value().values()))
        super().__init__(node)

    def get_next_view(self) -> SingleCommentView | None:
        if isinstance(self.obj, dict):
            return None
        return SingleCommentView(self.obj)


class PageView(CongruenceTextBox):
    """Text box showing metadata for a Confluence page."""

    def __init__(self, obj: Any) -> None:
        self.obj = obj
        self.title = "Page"
        content = obj._data["content"]
        try:
            history = content["history"]
            update = history["lastUpdated"]
            infos = {
                "Title": obj.get_title(),
                "Space": content["space"]["name"],
                "Space key": content["space"]["key"],
                "Created by": history["createdBy"]["displayName"],
                "Created at": convert_date(history["createdDate"]),
                "Last updated by": update["by"]["displayName"],
                "Last updated at": convert_date(update["when"]),
                "Last change message": update["message"],
                "Version number": update["number"],
            }
            text = "\n".join(f"{k}: {v}" for k, v in infos.items())
        except KeyError as e:
            self.app.alert(f"KeyError ({e}), displaying raw data", "error")
            text = obj.get_json()
        help_string = cs.PAGE_VIEW_HELP
        super().__init__(text, help_string=help_string)

    @key_action
    def list_diff(self, size: tuple | None = None) -> None:
        try:
            view = DiffView(self.obj.content.id)
            self.app.push_view(view)
        except KeyError:
            self.app.alert("No diff available", "warning")

    @key_action
    def cli_browser(self, size: tuple | None = None) -> None:
        open_content_in_cli_browser(self.app, self.obj.content.id)

    @key_action
    def gui_browser(self, size: tuple | None = None) -> None:
        url = f"pages/viewpage.action?pageId={self.obj.content.id}"
        open_gui_browser(url)

    @key_action
    def go_to_comments(self, size: tuple | None = None) -> None:
        page_id = self.obj.content.id
        view = CommentContextView(page_id, self.obj)
        self.app.push_view(view)

    @key_action
    def like(self, size: tuple | None = None) -> None:
        if self.obj.content.toggle_like():
            if self.obj.content.liked:
                self.app.alert("You liked this", "info")
            else:
                self.app.alert("You unliked this", "info")
        else:
            self.app.alert("Like failed", "error")


class DiffView(CongruenceTextBox):
    def __init__(self, page_id: str, first: int | None = None, second: int | None = None) -> None:
        self.page_id = page_id
        self.title = "Diff"
        url = f"rest/api/content/{page_id}"
        params: dict[str, Any] = {"expand": "version,body.view"}

        if first is not None:
            params["status"] = "historical"
            params["version"] = first
        r = make_request(url, params=params)
        data = r.json()
        self.first: int = data["version"]["number"]
        self.version1: str = data["body"]["view"]["value"]
        tofile = (
            f"Version number {self.first} by "
            f"{data['version']['by']['displayName']}, "
            f"{convert_date(data['version']['when'])}"
        )

        self.second: int = (self.first - 1) if second is None else second
        params["version"] = self.second
        params["status"] = "historical"

        r = make_request(url, params=params)
        data = r.json()
        self.version2: str = data["body"]["view"]["value"]
        fromfile = (
            f"Version number {self.second} by "
            f"{data['version']['by']['displayName']}, "
            f"{convert_date(data['version']['when'])}"
        )

        self.diff: str = create_diff(self.version2, self.version1, fromfile=fromfile, tofile=tofile, html=True)
        if not self.diff:
            self.diff = cs.DIFF_EMPTY
        help_string = cs.DIFF_VIEW_HELP
        super().__init__(self.diff, color=True, help_string=help_string)

    @key_action
    def cycle_next(self, size: tuple | None = None) -> None:
        try:
            view = DiffView(self.page_id, self.first - 1, self.second - 1)
            self.app.pop_view()
            self.app.push_view(view)
        except KeyError:
            self.app.alert("No diff available", "warning")

    @key_action
    def cycle_prev(self, size: tuple | None = None) -> None:
        try:
            view = DiffView(self.page_id, self.first + 1, self.second + 1)
            self.app.pop_view()
            self.app.push_view(view)
        except KeyError:
            self.app.alert("No diff available", "warning")


class ContentList(CongruenceListBox):
    """A list box that can display Confluence content objects."""

    def __init__(self, EntryClass: type = ColumnListBoxEntry, help_string: str = "") -> None:
        self.title = "Content"
        self._entryclass = EntryClass
        self.params: dict[str, Any] = {
            "cql": "",
            "start": 0,
            "limit": 20,
        }
        self.entries: list = []
        super().__init__(self.entries, help_string=help_string)

    @key_action
    def load_more(self, size: tuple | None = None) -> None:
        log.info("Load more ...")
        self.entries += self.get_entries()
        self.redraw()

    @key_action
    def load_much_more(self, size: tuple | None = None) -> None:
        log.info("Load much more ...")
        self.params["limit"] *= 5
        self.entries += self.get_entries()
        self.params["limit"] //= 5
        self.redraw()

    @key_action
    def update(self, size: tuple | None = None) -> None:
        log.info("Update ...")
        self.params["start"] = 0
        self.entries = self.get_entries()
        self.redraw()

    @key_action
    def cli_browser(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        open_content_in_cli_browser(self.app, node.obj.content.id)

    @key_action
    def gui_browser(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        obj_id = node.obj.content.id
        if not obj_id:
            self.app.alert("Object has no ID", "error")
            return
        url = f"pages/viewpage.action?pageId={obj_id}"
        open_gui_browser(url)

    def get_entries(self) -> list:
        r = make_request("rest/api/search", params=self.params)
        result = []
        response = r.json()
        if r.ok and response:
            for each in response["results"]:
                obj = ContentWrapper(each)
                try:
                    if not getattr(obj.content, "blacklisted", False):
                        result.append(self._entryclass(obj))
                except AttributeError:
                    result.append(self._entryclass(obj))
            self.app.alert(f"Received {len(result)} items", "info")
            self.params["start"] += self.params["limit"]
        return result


def open_content_in_cli_browser(app: Any, obj_id: str) -> None:
    log.debug(f"Build HTML view for page with id '{obj_id}'")
    if not obj_id:
        app.alert("Object has no ID", "error")
        return
    r = make_request(f"rest/api/content/{obj_id}?expand=body.view")
    if not r.ok:
        app.alert(f"Request failed ({r.status_code})", "error")
        return
    content = r.json()["body"]["view"]["value"]
    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{content}</body></html>"
    open_doc_in_cli_browser(html.encode(), app)
