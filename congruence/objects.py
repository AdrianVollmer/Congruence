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
        'user': User,
    }
    if 'content' in data:
        if 'type' in data['content']:
            return type_map[data['content']['type']]
    if 'entityType' in data:
        return type_map[data['entityType']]
    raise KeyError("Unkown confluence object")


class ConfluenceObject(ABC):
    @abstractmethod
    def get_title(self, cols=False):
        pass

    @abstractmethod
    def get_json(self):
        pass


class ContentObject(ConfluenceObject):
    def __init__(self, data):
        self._data = data
        if 'content' in data:
            self.url = data['url']
            content = data['content']
        else:
            self.url = data['_links']['webui']
            content = data
        self.id = content['id']
        self.title = content['title']
        #  self.space = data['space']
        self.liked = False  # TODO determine

    def get_title(self, cols=False):
        if cols:
            content = self._data['content']
            lastUpdated = content['history']['lastUpdated']
            if 'space' in content:
                space = content['space']['key']
            else:
                space = '?'
            title = [
                content['type'][0].upper(),
                space,
                lastUpdated['by']['displayName'],
                convert_date(lastUpdated['when'], 'friendly'),
                content['title'],
            ]
            return title
        return self.title

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)

    def match(self, search_string):
        return re.match(search_string, self.title)

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
        try:
            self.author = self._data['version']['by']['displayName']
        except KeyError as e:
            log.exception(e)
            self.author = 'unknown'

    def get_title(self, cols=False):
        if cols:
            return super().get_title(cols=True)
        date = self._data['version']['when']
        date = convert_date(date)
        title = '%s, %s' % (
            self._data['version']['by']['displayName'],
            date,
        )
        return title
        #  return {
        #      "title": title,
        #      "username": self._data["version"]["by"]["username"],
        #      "displayName": self._data["version"]["by"]["displayName"],
        #      "date": date,
        #      "url": self._data["_links"]["webui"],
        #      "versions": str(self._data["version"]["number"]),
        #      # TODO insert selection of inline comments
        #  }

    def get_content(self):
        #  log.debug(self._data)
        return html_to_text(self._data['body']['view']['value'])

    def get_parent_container(self):
        #  log.debug(self._data)
        return self._data['content']['_expandable']['container']

    def send_reply(self, text):
        page_id = self._data['ancestors'][0]['_expandable']['container']
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
        return (
            re.match(search_string, self.get_title())
            or re.match(search_string, self.get_content())
        )


class Attachment(ContentObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'attachment'
        self.short_type = 'A'
        self.download = data['_links']['download']


class User(ConfluenceObject):
    def __init__(self, data):
        self._data = data
        self.type = 'user'
        super().__init__()

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

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)


class Space(ConfluenceObject):
    def __init__(self, data):
        self._data = data
        self.key = data['key']
        self.name = data['name']

    def get_title(self):
        return self.name

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)
