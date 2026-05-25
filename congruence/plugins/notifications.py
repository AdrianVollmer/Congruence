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

"""Notifications plugin for Confluence."""

from __future__ import annotations

import json
import re

from congruence.interface import convert_date, html_to_text, make_request
from congruence.objects import ConfluenceObject
from congruence.views.common import CongruenceTextBox, key_action
from congruence.views.listbox import ColumnListBoxEntry, CongruenceListBox

__help__ = """Confluence Notifications

This view displays your latest notifications.

"""


class NotificationView(CongruenceListBox):
    def __init__(self, properties: dict | None = None) -> None:
        self.title = "Notifications"
        props = properties or {}
        self.fetch_limit: int = props.get("Limit", 20)
        self.entries = self.get_notifications()
        super().__init__(self.entries, help_string=__help__)

    def get_notifications(self, before: str | None = None) -> list:
        params: dict = {"limit": self.fetch_limit}
        if before:
            params["before"] = before
        r = make_request("rest/mywork/latest/notification", params=params)
        notifications = [NotificationEntry(NotificationObject(e)) for e in r.json()]
        self.app.alert(f"Received {len(notifications)} items", "info")
        return notifications

    @key_action
    def load_more(self, size: tuple | None = None) -> None:
        last = self.entries[-1].obj._data["id"]
        self.entries += self.get_notifications(before=last)
        self.redraw()


class NotificationEntry(ColumnListBoxEntry):
    def get_next_view(self) -> CongruenceTextBox:
        obj: NotificationObject = self.obj  # type: ignore[assignment]
        d = obj._data
        text = d["title"] + "\n"
        if "title" in d:
            text += f"Title: {d['item']['title']}\n"
        text += f"Created: {convert_date(d['created'])}\n"
        if d["created"] != d["updated"]:
            text += f"Updated: {convert_date(d['updated'])}\n"
        if "highlightText" in obj.metadata:
            text += f"\n> {obj.metadata['highlightText']}\n"
        if "description" in d:
            text += "\n" + html_to_text(d["description"], replace_emoticons=True) + "\n"
        view = CongruenceTextBox(text)
        view.title = "Notification"
        return view

    def search_match(self, search_string: str) -> bool:
        obj: NotificationObject = self.obj  # type: ignore[assignment]
        return obj.match(search_string)


class NotificationObject(ConfluenceObject):
    def __init__(self, data: dict) -> None:
        self._data = data
        self.metadata: dict = self._data.get("metadata", {})
        try:
            self.title: str = self._data["item"]["title"]
        except KeyError:
            self.title = self._data.get("title", "")

    def get_title(self) -> str:
        return self.title

    def get_columns(self) -> list[str]:
        try:
            entity = self._data["entity"][0].upper()
        except KeyError:
            entity = "?"
        if self.metadata:
            user = self.metadata.get("user", "?")
            action = self._data.get("action", "?")
        else:
            user = "?"
            action = "?"
        return [
            entity,
            user,
            action,
            convert_date(self._data["updated"], "friendly"),
            self.title,
        ]

    def get_json(self) -> str:
        return json.dumps(self._data, indent=2, sort_keys=True)

    def match(self, search_string: str) -> bool:
        return bool(re.search(search_string, self.title))


PluginView = NotificationView
