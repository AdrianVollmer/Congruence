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
    """Base class for all Confluence content objects (pages, comments, users, spaces, ...)."""

    def __init__(self, data: dict) -> None:
        self._data = data
        self.object_id: str = data.get("id", "")
        log.debug(json.dumps(data, indent=2))

    @abstractmethod
    def get_title(self) -> str:
        """Return a human-readable title string."""

    @abstractmethod
    def get_columns(self) -> list[str]:
        """Return a list of exactly five column strings for list display."""

    @property
    def id(self) -> str:
        return self.object_id

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
        self.title: str = data["title"]
        self.type: str = data.get("type", "?")

        history = data.get("history", {})
        last_updated = history.get("lastUpdated", {})
        self.versionby: User = User(last_updated["by"])
        self.last_updated_when: str = last_updated.get("when", "")
        self.created_date: str = history.get("createdDate", "")
        created_by = history.get("createdBy")
        self.created_by: User | None = User(created_by) if created_by else None

        version = data.get("version", {})
        self.version_number: int = version.get("number", 0)
        self.version_message: str = version.get("message", "")

        links = data.get("_links", {})
        self.webui_url: str = links.get("webui", "")

        space_data = data.get("space")
        self.space: Space | None = Space(space_data) if space_data else None

        self.blacklisted: bool = is_blacklisted_user(self.versionby.username)
        self.liked: bool = False

    def get_title(self) -> str:
        return self.title

    def get_columns(self) -> list[str]:
        return [
            self.type[0].upper(),
            self.space.key if self.space else "?",
            self.versionby.display_name,
            convert_date(self.last_updated_when, "friendly"),
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

        self.url: str = data.get("_links", {}).get("webui", "")
        self.body_html: str = data.get("body", {}).get("view", {}).get("value", "")
        self.container_path: str = data.get("_expandable", {}).get("container", "")

        ancestors = data.get("ancestors", [])
        try:
            self.ancestor_root_link: str | None = ancestors[0]["_links"]["self"]
        except (IndexError, KeyError):
            self.ancestor_root_link = None

        username = self.versionby.display_name
        if self.blacklisted:
            username = "<blocked user>"
        self.head: str = f"{username}, {convert_date(self.created_date)}"

        self.ref: str | None = None
        self.is_inline: bool = False
        extensions = data.get("extensions", {})
        inline_properties = extensions.get("inlineProperties")
        if inline_properties is not None:
            self.ref = inline_properties.get("originalSelection")
            if self.ref:
                self.head += " (inline comment)"
                self.is_inline = True

    def get_title(self) -> str:
        return self.title

    def get_columns(self) -> list[str]:
        return [
            self.type[0].upper(),
            self.space.key if self.space else "?",
            self.versionby.display_name,
            convert_date(self.last_updated_when, "friendly"),
            self.get_title(),
        ]

    def get_head(self) -> str:
        return self.head

    def get_content(self) -> str:
        if self.blacklisted:
            return ""
        comment = html_to_text(self.body_html, replace_emoticons=True)
        if self.ref:
            comment = f"> {self.ref}\n\n{comment}"
        return comment

    def send_reply(self, text: str) -> bool:
        if self.is_inline:
            return self.send_inline_reply(text)
        return self.send_comment_reply(text)

    def send_comment_reply(self, text: str) -> bool:
        m = re.search(r"/([^/]*$)", self.container_path)
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
        m = re.search(r"/([^/]*$)", self.container_path)
        if m is None:
            log.error("Could not extract page ID from container path")
            return False
        page_id = m.group(1)

        if self.ancestor_root_link is not None:
            m2 = re.search(r"/([^/]*$)", self.ancestor_root_link)
            root_id = m2.group(1) if m2 else self.object_id
        else:
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
        self.display_name: str = data["displayName"]
        self.username: str = data["username"]

    def get_title(self) -> str:
        return self.display_name

    def get_columns(self) -> list[str]:
        return [
            self.type[0].upper(),
            "",
            self.display_name,
            "?",
            "",
        ]


class Space(ConfluenceObject):
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.type: str = "space"
        self.key: str = data["key"]
        self.name: str = data["name"]
        self.date: str = convert_date(data["timestamp"], "friendly") if "timestamp" in data else "?"
        # Space directory API provides links as an array; content API nests under _links
        self.gui_url: str = ""
        try:
            self.gui_url = data["link"][1]["href"]
        except (KeyError, IndexError):
            self.gui_url = data.get("_links", {}).get("webui", "")

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
        self.title: str = data.get("title", "Generic object")

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
        self.entity_type: str = data["entityType"]
        content_data: dict = data[self.entity_type]
        self.type: str = content_data["type"]
        cls = self.type_map.get(self.type)
        if cls is not None:
            self.content: ConfluenceObject = cls(content_data)
        else:
            log.error(f"Unknown entity type: {self.type}")
            self.content = Generic(content_data)
        self.title: str = self.content.get_title()
        parent = data.get("resultParentContainer", {})
        self.parent_url: str = parent.get("displayUrl", "")

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
