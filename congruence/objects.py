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

"""Classes representing content objects in Confluence."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import ClassVar
from uuid import uuid4

from congruence.args import config
from congruence.interface import convert_date, html_to_text, make_request, md_to_html
from congruence.logging import log


def is_blacklisted_user(username: str) -> bool:
    return "UserBlacklist" in config and username in config["UserBlacklist"]


class ConfluenceObject(ABC):
    """Base class for all Confluence content objects (pages, comments, users, spaces, …)."""

    def __init__(self, data: dict) -> None:
        self._data = data
        log.debug(json.dumps(data, indent=2))

    @abstractmethod
    def get_title(self) -> str:
        """Return a human-readable title string."""

    @abstractmethod
    def get_columns(self) -> list[str]:
        """Return a list of exactly five column strings for list display."""

    @property
    def id(self) -> str:
        return self._data.get("id", "")

    def get_json(self) -> str:
        return json.dumps(self._data, indent=2, sort_keys=True)

    def get_content(self) -> str:
        """Return the body text for a carded list entry."""
        return ""

    def get_head(self) -> str:
        """Return the header text for a carded list entry."""
        return self.get_title()

    def match(self, search_string: str) -> bool:
        return bool(re.search(search_string, self.get_title()) or re.search(search_string, self.get_content()))


class Content(ConfluenceObject):
    """Base class for Pages, Blogposts, Comments, and Attachments."""

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.title: str = self._data["title"]
        self.type: str = self._data.get("type", "?")
        self.object_id: str = self._data["id"]  # explicit str for subclass use
        self.versionby: User = User(self._data["history"]["lastUpdated"]["by"])
        try:
            self.space: Space | None = Space(self._data["space"])
        except KeyError:
            self.space = None
        self.blacklisted: bool = is_blacklisted_user(self.versionby.username)
        self.liked: bool = False

    @property
    def id(self) -> str:  # type: ignore[override]
        return self.object_id

    def get_title(self) -> str:
        return self._data["title"]

    def get_columns(self) -> list[str]:
        last_updated = self._data["history"]["lastUpdated"]
        return [
            self.type[0].upper(),
            self.space.key if self.space else "?",
            self.versionby.display_name,
            convert_date(last_updated["when"], "friendly"),
            self.get_title(),
        ]

    def like(self) -> bool:
        log.debug(f"Liking {self.object_id}")
        headers = {"Content-Type": "application/json"}
        r = make_request(
            f"rest/likes/1.0/content/{self.object_id}/likes",
            method="POST",
            headers=headers,
            data="",
        )
        if r.status_code == 200:
            self.liked = True
            return True
        if r.status_code == 400:
            # Already liked
            self.liked = True
            return True
        log.error("Like failed")
        return False

    def unlike(self) -> bool:
        log.debug(f"Unliking {self.object_id}")
        r = make_request(
            f"rest/likes/1.0/content/{self.object_id}/likes",
            method="DELETE",
            data="",
        )
        if r.status_code == 200:
            self.liked = False
            return True
        log.error("Unlike failed")
        return False

    def toggle_like(self) -> bool:
        if self.liked:
            return self.unlike()
        return self.like()

    def match(self, search_string: str) -> bool:
        return bool(
            re.search(search_string, self.get_title())
            or re.search(search_string, self.get_content())
        )


class Page(Content):
    pass


class Blogpost(Page):
    pass


class Comment(Content):
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.type = "comment"

        date = convert_date(self._data["history"]["createdDate"])
        self.url: str = data["_links"]["webui"]
        username = self.versionby.display_name
        if self.blacklisted:
            username = "<blocked user>"
        self.head: str = f"{username}, {date}"
        self.ref: str | None = None
        self.is_inline: bool = False
        try:
            extensions = self._data["extensions"]
            inline_properties = extensions["inlineProperties"]
            self.ref = inline_properties["originalSelection"]
            self.head += " (inline comment)"
            self.is_inline = True
        except KeyError:
            pass

    def get_title(self) -> str:
        return self.title

    def get_columns(self) -> list[str]:
        last_updated = self._data["history"]["lastUpdated"]
        return [
            self.type[0].upper(),
            self.space.key if self.space else "?",
            self.versionby.display_name,
            convert_date(last_updated["when"], "friendly"),
            self.get_title(),
        ]

    def get_head(self) -> str:
        return self.head

    def get_content(self) -> str:
        if self.blacklisted:
            return ""
        comment = html_to_text(self._data["body"]["view"]["value"], replace_emoticons=True)
        if self.ref:
            comment = f"> {self.ref}\n\n{comment}"
        return comment

    def send_reply(self, text: str) -> bool:
        if self.is_inline:
            return self.send_inline_reply(text)
        return self.send_comment_reply(text)

    def send_comment_reply(self, text: str) -> bool:
        page_id_path = self._data["_expandable"]["container"]
        m = re.search(r"/([^/]*$)", page_id_path)
        if m is None:
            log.error("Could not extract page ID from container path")
            return False
        page_id = m.group(1)
        url = f"/rest/tinymce/1/content/{page_id}/comments/{self.object_id}/comment"
        params = {"actions": "true"}
        answer = md_to_html(text, url_encode="html")
        uuid = str(uuid4())
        headers = {"X-Atlassian-Token": "no-check"}
        data = f"{answer}&watch=false&uuid={uuid}"
        r = make_request(url, params, method="POST", data=data, headers=headers, no_token=True)
        return r.status_code == 200

    def send_inline_reply(self, text: str) -> bool:
        page_id_path = self._data["_expandable"]["container"]
        m = re.search(r"/([^/]*$)", page_id_path)
        if m is None:
            log.error("Could not extract page ID from container path")
            return False
        page_id = m.group(1)

        try:
            root_link = self._data["ancestors"][0]["_links"]["self"]
            m2 = re.search(r"/([^/]*$)", root_link)
            root_id = m2.group(1) if m2 else self.object_id
        except IndexError:
            root_id = self.object_id

        url = f"rest/inlinecomments/1.0/comments/{root_id}/replies"
        params = {"containerId": page_id}
        data = {"body": md_to_html(text), "commentId": int(root_id)}
        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        r = make_request(url, params, method="POST", data=json.dumps(data), headers=headers)
        if r.status_code == 200:
            return True
        log.debug(r.request.headers)
        log.debug(r.request.body)
        log.debug(r.text)
        return False


class Attachment(Content):
    pass


class User(ConfluenceObject):
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.type: str = "user"
        self.date: str = "?"
        self.display_name: str = self._data["displayName"]
        self.username: str = self._data["username"]

    def get_title(self) -> str:
        return self.display_name

    def get_columns(self) -> list[str]:
        return [
            self.type[0].upper(),
            "",
            self.display_name,
            self.date,
            "",
        ]


class Space(ConfluenceObject):
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.type: str = "space"
        self.key: str = self._data["key"]
        self.name: str = self._data["name"]
        try:
            self.date: str = convert_date(self._data["timestamp"], "friendly")
        except KeyError:
            self.date = "?"

    def get_title(self) -> str:
        return self.name

    def get_columns(self) -> list[str]:
        return [
            self.type[0].upper(),
            self.key,
            self.name,
            self.date,
            "",
        ]


class Generic(ConfluenceObject):
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.type: str = "?"
        log.debug(json.dumps(data, indent=2))
        self.object_id: str | None = None
        self.title: str = self._data.get("title", "Generic object")

    def get_title(self) -> str:
        return self.title

    def get_columns(self) -> list[str]:
        return ["?", "?", "?", "?", self.title]


class ContentWrapper:
    """Wrapper that resolves the entity type returned by the Confluence search API."""

    type_map: ClassVar[dict[str, type[ConfluenceObject]]] = {
        "page": Page,
        "blogpost": Blogpost,
        "comment": Comment,
        "attachment": Attachment,
        "space": Space,
        "personal": Space,
        "user": User,
        "known": User,
    }

    def __init__(self, data: dict) -> None:
        self._data = data
        content_data: dict = data[data["entityType"]]
        self.type: str = content_data["type"]
        try:
            self.content: ConfluenceObject = self.type_map[self.type](content_data)
        except KeyError:
            log.error(f"Unknown entity type: {self.type}")
            self.content = Generic(content_data)
        self.title: str = self.content.get_title()

    def get_title(self) -> str:
        return self.content.get_title()

    def get_columns(self) -> list[str]:
        return self.content.get_columns()

    def get_head(self) -> str:
        return self.content.get_head()

    def match(self, search_string: str) -> bool:
        return self.content.match(search_string)

    def get_content(self) -> str:
        return self.content.get_content()

    def get_json(self) -> str:
        return json.dumps(self._data, indent=2, sort_keys=True)
