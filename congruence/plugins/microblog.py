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

"""Microblog plugin for Confluence."""

from __future__ import annotations

import urwid

import congruence.strings as cs
from congruence.external import open_gui_browser
from congruence.interface import convert_date, html_to_text, make_request, md_to_html
from congruence.logging import log
from congruence.objects import Content, is_blacklisted_user
from congruence.views.common import CongruenceTextBox, key_action
from congruence.views.listbox import CardedListBoxEntry, CongruenceListBox

__help__ = """Congruence Microblog

Here you can see the latest entries of the microblog plugin.

"""


class MicroblogView(CongruenceListBox):
    def __init__(self, properties: dict | None = None) -> None:
        self.title = "Microblog"
        self.properties = properties or {}
        self.limit: int = 20
        self.replyLimit: int = 999
        self.post_data: str = ""
        self.offset: int = 0
        self.update()
        super().__init__(self.entries, help_string=__help__)

    @key_action
    def update(self, size: tuple | None = None) -> None:
        params = self.properties.get("Parameters", {})
        self.limit = params.get("limit", 20)
        self.replyLimit = params.get("replyLimit", 999)
        self.post_data = self.properties.get("Data", "")
        self.offset = 0
        self.entries = self._get_microblog()
        self.app.alert(f"Received {len(self.entries)} items", "info")
        if hasattr(self, "walker"):
            self.redraw()

    @key_action
    def load_more(self, size: tuple | None = None) -> None:
        self.entries += self._get_microblog()
        self.redraw()

    def _get_microblog(self) -> list:
        log.info("Fetch microblog...")
        response = make_request(
            "rest/microblog/1.0/microposts/search",
            params={"offset": self.offset, "limit": self.limit, "replyLimit": self.replyLimit},
            method="POST",
            data=self.post_data,
            headers={"Content-Type": "application/json"},
        )
        result = [MicroblogEntry(MicroblogObject(e), is_reply=False) for e in response.json()["microposts"]]
        self.offset += len(result)
        return result

    @key_action
    def gui_browser(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        post_id = node.obj._data["id"]
        open_gui_browser(f"plugins/micropost/view.action?postId={post_id}")

    @key_action
    def post_comment(self, size: tuple | None = None) -> None:
        topic_id = 16
        post_id = _send_sketch(topic_id)
        if not post_id:
            self.app.alert("Failed to send sketch", "error")
            return
        reply = self.app.get_long_input(cs.REPLY_MSG)
        if not reply:
            self.app.alert("Reply empty, aborting", "warning")
            return
        reply = md_to_html(reply, url_encode="html")
        headers = {
            "X-Atlassian-Token": "no-check",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        data = f"{reply}&topicId={topic_id}&spaceKey=~admin"
        r = make_request(
            f"rest/microblog/1.0/microposts/{post_id}", method="PUT", data=data, headers=headers, no_token=True
        )
        if r.status_code == 200:
            self.app.alert("Microblog post sent", "info")
        else:
            self.app.alert("Failed to send microblog post", "error")


class MicroblogEntry(CardedListBoxEntry):
    """Represents a microblog post or reply."""

    def __init__(self, obj: MicroblogObject, is_reply: bool = False) -> None:
        self.obj = obj
        self.is_reply = is_reply
        super().__init__(self.obj)

    def get_next_view(self) -> CongruenceTextBox | MicroblogReplyView:
        if not self.is_reply:
            return MicroblogReplyView(self.obj._data)
        d = self.obj._data
        text = f"Author: {d['authorFullName']}\n"
        text += f"Date: {convert_date(d['lastModificationDate'])}\n"
        likes = ", ".join(u["userFullname"] for u in d["likingUsers"])
        text += f"Likes: {likes}"
        view = CongruenceTextBox(text)
        view.title = "Post"
        return view

    def search_match(self, search_string: str) -> bool:
        return self.obj.match(search_string)


class MicroblogObject(Content):
    def __init__(self, data: dict) -> None:
        self._data = data
        self.blacklisted: bool = is_blacklisted_user(self._data["authorName"])

    def get_title(self) -> str:
        like_number = len(self._data["likingUsers"])
        likes = ""
        if like_number > 0:
            if like_number == 1 and self._data["hasLiked"]:
                likes = " - You liked this"
            else:
                likes = f" - {like_number} likes"
                if self._data["hasLiked"]:
                    likes += ", including you"
        replies = f" - {len(self._data['replies'])} replies" if self._data["replies"] else ""
        author = self._data["authorFullName"] if not self.blacklisted else "<blocked user>"
        return f"{author} ({convert_date(self._data['lastModificationDate'])}){replies}{likes}"

    def get_head(self) -> str:
        return self.get_title()

    def get_content(self) -> str:
        if self.blacklisted:
            return ""
        return html_to_text(self._data["renderedContent"]).strip()

    def get_columns(self) -> list[str]:
        return ["", "", self.get_title(), "", ""]

    def match(self, search_string: str) -> bool:
        import re
        return bool(re.search(search_string, self.get_title()) or re.search(search_string, self.get_content()))


def _send_sketch(topic_id: int) -> str | None:
    """Obtain a post ID for a new microblog entry."""
    headers = {
        "X-Atlassian-Token": "no-check",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    r = make_request(
        "rest/microblog/1.0/sketch",
        method="POST",
        data=f"topicId={topic_id}",
        headers=headers,
        no_token=True,
    )
    if r.status_code != 200:
        return None
    return r.text


class MicroblogReplyView(CongruenceListBox):
    def __init__(self, entries: dict) -> None:
        self.title = "Replies"
        items = [MicroblogEntry(MicroblogObject(entries), is_reply=True)]
        items += [MicroblogEntry(MicroblogObject(e), is_reply=True) for e in entries["replies"]]
        super().__init__(items, help_string=__help__)

    @key_action
    def like(self, size: tuple | None = None) -> None:
        obj = self.focus.obj
        post_id = obj._data["id"]
        r = make_request(
            f"rest/microblog/1.0/microposts/{post_id}/like",
            method="POST",
            headers={"X-Atlassian-Token": "no-check"},
            no_token=True,
        )
        if r.status_code == 200:
            msg = "You liked this" if r.text == "true" else "You unliked this"
            self.app.alert(msg, "info")
        else:
            self.app.alert("Like failed", "error")

    @key_action
    def reply(self, size: tuple | None = None) -> None:
        obj = self.entries[0].obj
        author = obj._data["authorFullName"]
        topic_id = obj._data["topic"]["id"]
        parent_id = obj._data["id"]

        post_id = _send_sketch(topic_id)
        if not post_id:
            self.app.alert("Failed to send sketch", "error")
            return

        prev_msg = "\n".join(f"## > {line}" for line in obj._data["renderedContent"].splitlines())
        help_text = cs.REPLY_MSG + f"## {author} wrote:\n{prev_msg}"
        reply = self.app.get_long_input(help_text)
        if not reply:
            self.app.alert("Reply empty, aborting", "warning")
            return
        reply = md_to_html(reply, url_encode="html")
        headers = {
            "X-Atlassian-Token": "no-check",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        r = make_request(
            f"rest/microblog/1.0/microposts/{post_id}",
            method="PUT",
            data=f"{reply}&parentId={parent_id}&spaceKey=~admin",
            headers=headers,
            no_token=True,
        )
        if r.status_code == 200:
            self.app.alert("Reply sent", "info")
        else:
            self.app.alert("Failed to send reply", "error")

    @key_action
    def gui_browser(self, size: tuple | None = None) -> None:
        obj = self.entries[0].obj
        open_gui_browser(f"plugins/micropost/view.action?postId={obj._data['id']}")


class MicroblogPost(CongruenceTextBox):
    def __init__(self, data: dict) -> None:
        self.title = "Post"
        max_len = max(len(k) for k in data)
        lines = [
            urwid.Columns([(max_len + 1, urwid.Text(k)), urwid.Text(str(v))])
            for k, v in data.items()
            if k != "renderedContent"
        ]
        super().__init__(lines)


class MicroblogReplyDetails(CongruenceListBox):
    def __init__(self, data: dict) -> None:
        self.title = "Details"
        max_len = max(len(k) for k in data)
        lines = [
            urwid.Columns([(max_len + 1, urwid.Text(k)), urwid.Text(str(v))])
            for k, v in data.items()
            if k != "renderedContent"
        ]
        super().__init__(lines)


PluginView = MicroblogView
