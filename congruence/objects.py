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


"""
This file contains classes which represent content objects in Confluence.
"""

from congruence.interface import convert_date
from congruence.logging import log

import json
import re
from abc import ABC, abstractmethod


def determine_type(data):
    """Try to determine which type of object it is"""
    type_map = {
        'page': Page,
        'blogpost': Blogpost,
        'comment': Comment,
        'attachment': Attachment,
        'personal': Space,
        #  'known': User,
    }
    log.debug(data)
    if 'content' in data:
        if 'type' in data['content']:
            return type_map[data['content']['type']]
    raise KeyError("Unkown confluence object")


class ConfluenceObject(ABC):
    @abstractmethod
    def get_title(self, cols=False):
        pass


class ContentObject(ConfluenceObject):
    def __init__(self, data):
        self._data = data
        self.id = data['content']["id"]
        self.title = data['content']["title"]
        #  self.space = data["space"]
        self.liked = False  # TODO determine

    def get_title(self, cols=False):
        if cols:
            content = self._data['content']
            lastUpdated = content['history']['lastUpdated']
            if 'space' in content:
                space = content["space"]["key"]
            else:
                space = "?"
            title = [
                content["type"][0].upper(),
                space,
                lastUpdated['by']["displayName"],
                convert_date(lastUpdated["when"], "friendly"),
                content["title"],
            ]
            return title
        return self.title

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)

    def match(self, search_string):
        return re.match(
            search_string,
            self._data['content']['title']
        )

    def get_content(self):
        # TODO load content if not in object already
        return self._data["content"]['_expandable']['container']

    #  def get_like_status(self):

    def like(self):
        id = self.id
        log.debug("Liking %s" % id)
        headers = {
            "Content-Type": "application/json",
        }
        r = make_request(f"rest/likes/1.0/content/{id}/likes",
                         method='POST',
                         headers=headers,
                         data="")
        if r.status_code == 200:
            self.liked = True
            return True
        if r.status_code == 400:
            # already liked
            self.liked = True
        log.error("Like failed")
        return False

    def unlike(self):
        id = self.id
        log.debug("Unliking %s" % id)
        r = make_request(f"rest/likes/1.0/content/{id}/likes",
                         method='DELETE',
                         #  headers=headers,
                         data="")

        if r.status_code == 200:
            self.liked = False
            return True
        log.error("Unlike failed")
        return False

    def toggle_like(self):
        if self.liked:
            return self.unlike()
        else:
            return self.like()


class Page(ContentObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'page'
        self.short_type = 'P'


class Blogpost(ContentObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'blogpost'
        self.short_type = 'B'


class Comment(ContentObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'comment'
        self.short_type = 'C'


class Attachment(ContentObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'attachment'
        self.short_type = 'A'
        self.download = data["_links"]["download"]


class User(ConfluenceObject):
    pass


class Space(ConfluenceObject):
    def __init__(self, data):
        self._data = data
        self.key = data['key']
        self.name = data['name']
