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

from congruence.interface import convert_date, html_to_text, md_to_html
from congruence.logging import log
from congruence.interface import make_request

import json
import re
from uuid import uuid4
from abc import ABC, abstractmethod


def determine_type(data):
    """Try to determine which type of object it is"""

    type_map = {
        'page': Page,
        'blogpost': Blogpost,
        'comment': Comment,
        'attachment': Attachment,
        'personal': Space,
        'space': Space,
        'user': User,
        'content': ContentObject,
    }
    try:
        if 'content' in data:
            if 'type' in data['content']:
                return type_map[data['content']['type']]
        if 'entityType' in data:
            return type_map[data['entityType']]
    except KeyError:
        return ContentObject


class ConfluenceObject(ABC):
    """Base class for all confluence objects

    Can be a page, a comment, a user, a space, anything.

    """

    @abstractmethod
    def get_title(self, cols=False):
        """Subclasses who implement this must return a string or a list of
        strings with len=5 if cols=True"""
        pass

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)

    def get_content(self):
        return ""


class ContentObject(ConfluenceObject):
    """Base class for content objects

    This is only for pages, blog posts, attachments and comments
    """

    def __init__(self, data):
        """Constructor

        :data: a json object representing the object
        """

        self._data = data
        content = data['content']
        try:
            self.url = data['url']
        except KeyError:
            self.url = None
        self.id = content['id']
        self.title = content['title']
        try:
            self.space = Space(content['space'])
        except KeyError:
            self.space = None
        self.versionby = User(content['history']['lastUpdated']['by'])
        self.type = content['type']

        self.liked = False  # TODO determine

    def get_title(self, cols=False):
        if cols:
            content = self._data['content']
            lastUpdated = content['history']['lastUpdated']
            title = [
                self.type[0].upper(),
                self.space.key,
                self.versionby.display_name,
                convert_date(lastUpdated['when'], 'friendly'),
                self.title,
            ]
            return title
        return self.title

    def match(self, search_string):
        return re.search(search_string, self.title)

    def get_content(self):
        # TODO load content if not in object already
        return self._data['content']['_expandable']['container']

    #  def get_like_status(self):

    def like(self):
        id = self.id
        log.debug("Liking %s" % id)
        headers = {
            'Content-Type': 'application/json',
        }
        r = make_request(f'rest/likes/1.0/content/{id}/likes',
                         method='POST',
                         headers=headers,
                         data='')
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
        r = make_request(f'rest/likes/1.0/content/{id}/likes',
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


class Blogpost(Page):
    def __init__(self, data):
        super().__init__(data)


class Comment(ContentObject):
    def __init__(self, data):
        super().__init__(data)
        date = self._data['content']['history']['createdDate']
        date = convert_date(date)
        self.title = '%s, %s' % (
            self.versionby.display_name,
            date,
        )
        self.ref = None
        try:
            extensions = self._data['content']['extensions']
            inline_properties = extensions['inlineProperties']
            self.ref = inline_properties['originalSelection']
            self.title += " (inline comment)"
        except KeyError:
            pass

    def get_content(self):
        #  log.debug(self._data)
        comment = html_to_text(
            self._data['content']['body']['view']['value'],
            replace_emoticons=True,
        )
        if self.ref:
            # TODO set in italics
            comment = f"> {self.ref}\n\n{comment}"
        return comment

    def send_reply(self, text):
        page_id = self._data['_expandable']['container']
        page_id = re.search(r'/([^/]*$)', page_id).groups()[0]
        comment_id = self._data['id']
        url = (f'/rest/tinymce/1/content/{page_id}/'
               f'comments/{comment_id}/comment')
        params = {'actions': 'true'}
        answer = md_to_html(text, url_encode='html')
        uuid = str(uuid4())
        headers = {
            'X-Atlassian-Token': 'no-check',
        }

        data = f'{answer}&watch=false&uuid={uuid}'
        r = make_request(url, params, method='POST', data=data,
                         headers=headers, no_token=True)
        if r.status_code == 200:
            return True
        return False

    def match(self, search_string):
        try:
            return (
                re.search(search_string, self.get_title())
                or re.search(search_string, self.get_content())
            )
        except KeyError:
            return re.search(search_string, self.title)


class Attachment(ContentObject):
    def __init__(self, data):
        super().__init__(data)
        try:
            self.download = data['_links']['download']
        except KeyError:
            self.download = ""


class User(ConfluenceObject):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self.display_name = self._data['displayName']
        self.username = self._data['username']

    def get_title(self, cols=False):
        if cols:
            return [
                'U',
                '',
                self._data['user']['displayName'],
                convert_date(self._data['timestamp'], 'friendly'),
                '',
            ]
        return self._data['title']


class Space(ConfluenceObject):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self.type = 'space'

        self.key = self._data['key']
        self.name = self._data['name']

    def get_title(self, cols=False):
        if cols:
            return [
                'S',
                self.key,
                self.name,
                convert_date(self._data['timestamp'], 'friendly'),
                '',
            ]
        else:
            return self.name

    def match(self, search_string):
        return re.search(search_string, self.name)
