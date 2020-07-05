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
from congruence.views.common import DataObject
import congruence.environment as env

import json
import re
from uuid import uuid4


def is_blacklisted_user(username):
    return (
        "UserBlacklist" in env.config
        and username in env.config["UserBlacklist"]
    )


class Content(DataObject):
    """Base class for Pages, Blogposts, Comments, Attachments"""

    def __init__(self, data):
        super().__init__(data)
        self.title = self._data['title']
        try:
            self.type = self._data['type']
        except KeyError:
            self.type = '?'
        self.id = self._data['id']
        self.versionby = User(self._data['history']['lastUpdated']['by'])
        try:
            self.space = Space(self._data['space'])
        except KeyError:
            self.space = None
        self.versionby = User(self._data['history']['lastUpdated']['by'])

        self.blacklisted = is_blacklisted_user(self.versionby.username)

        self.liked = False  # TODO determine

    def get_title(self):
        return self._data['title']

    def get_columns(self):
        content = self._data
        lastUpdated = content['history']['lastUpdated']
        result = [
            self.type[0].upper(),
            self.space.key if self.space else '?',
            self.versionby.display_name,
            convert_date(lastUpdated['when'], 'friendly'),
            self.get_title(),
        ]
        return result

    #  def get_like_status(self):

    def get_html_content(self):
        if not hasattr(self, "id"):
            return ""
        log.debug("Build HTML view for page with id '%s'" % self.id)
        rest_url = f"rest/api/content/{self.id}?expand=body.storage"
        r = make_request(rest_url)
        content = r.json()
        content = content['body']['storage']['value']

        content = f'<html><head></head><body>{content}</body></html>'
        return content

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

    def match(self, search_string):
        return (
            re.search(search_string, self.get_title())
            or re.search(search_string, self.get_content())
        )


def post_comment(text, page_id, comment_id=None):
    """Post a comment to a page or as a reply to another comment

    :page_id: ID of the page
    :comment_id: ID of the comment you want to reply to; None for
        top level comment
    """

    if comment_id:
        url = (f'/rest/tinymce/1/content/{page_id}/'
               f'comments/{comment_id}/comment')
    else:
        url = f'/rest/tinymce/1/content/{page_id}/comment'
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


class Page(Content):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'page'


class Blogpost(Page):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'blogpost'


class Comment(Content):
    def __init__(self, data):
        super().__init__(data)
        self.type = 'comment'
        page_id = self._data['_expandable']['container']
        page_id = re.search(r'/([^/]*$)', page_id).groups()[0]

        date = self._data['history']['createdDate']
        self.url = data['_links']['webui']
        date = convert_date(date)
        username = self.versionby.display_name
        if self.blacklisted:
            username = "<blocked user>"
        self.head = '%s, %s' % (username, date)
        self.ref = None
        self.is_inline = False
        try:
            extensions = self._data['extensions']
            inline_properties = extensions['inlineProperties']
            self.ref = inline_properties['originalSelection']
            self.head += " (inline comment)"
            self.is_inline = True
        except KeyError:
            pass

    def get_title(self):
        return self.title

    def get_columns(self):
        content = self._data
        lastUpdated = content['history']['lastUpdated']
        result = [
            self.type[0].upper(),
            self.space.key if self.space else '?',
            self.versionby.display_name,
            convert_date(lastUpdated['when'], 'friendly'),
            self.get_title(),
        ]
        return result

    def get_head(self):
        return self.head

    def get_content(self):
        #  log.debug(self._data)
        if self.blacklisted:
            return ""
        try:
            comment = html_to_text(
                self._data['body']['view']['value'],
                replace_emoticons=True,
            )
            if self.ref:
                # TODO set in italics
                comment = f"> {self.ref}\n\n{comment}"
            return comment
        except KeyError:
            return ""

    def send_reply(self, text):
        if self.is_inline:
            self.send_inline_reply(text)
        else:
            self.send_comment_reply(text)

    def send_comment_reply(self, text):
        post_comment(text, self.page_id, self.id)

    def send_inline_reply(self, text):
        try:
            root_id = self._data['ancestors'][0]['_links']['self']
            root_id = re.search(r'/([^/]*$)', root_id).groups()[0]
        except IndexError:
            # It's the root element already
            root_id = self.id

        url = f"rest/inlinecomments/1.0/comments/{root_id}/replies"
        params = {
            'containerId': self.page_id,
        }
        data = {
            "body": md_to_html(text),
            "commentId": int(root_id),
        }
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        }
        r = make_request(url, params, method='POST', data=json.dumps(data),
                         headers=headers)
        if r.status_code != 200:
            raise RuntimeError("Sending reply failed")
        #  log.debug(r.request.headers)
        #  log.debug(r.request.body)
        #  log.debug(r.text)


class Attachment(Content):
    pass


class User(DataObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = "user"

        self._data = data
        self.date = '?'
        #  log.debug(self.get_json())
        self.display_name = self._data['displayName']
        self.username = self._data['username']

    def get_title(self):
        return self.display_name

    def get_columns(self):
        return [
            self.type[0].upper(),
            '',
            self.display_name,
            self.date,
            '',
        ]


class Space(DataObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = "space"

        self.key = self._data['key']
        self.name = self._data['name']
        try:
            self.date = convert_date(self._data['timestamp'], 'friendly')
        except KeyError:
            self.date = '?'

    def get_title(self):
        return self.name

    def get_columns(self):
        return [
            self.type[0].upper(),
            self.key,
            self.name,
            self.date,
            '',
        ]


class Generic(DataObject):
    def __init__(self, data):
        super().__init__(data)
        self.type = '?'
        log.debug(json.dumps(data, indent=2))
        self.id = None
        try:
            self.title = self._data['title']
        except KeyError:
            self.title = "Generic object"

    def get_title(self):
        return self.title

    def get_columns(self):
        return [
            '?',
            '?',
            '?',
            '?',
            self.title,
        ]


class ContentWrapper(object):
    """Class for content wrapper objects

    This is only for pages, blog posts, attachments and comments
    """

    type_map = {
        'page': Page,
        'blogpost': Blogpost,
        'comment': Comment,
        'attachment': Attachment,
        'space': Space,
        'global': Space,
        'personal': Space,
        'user': User,
        'known': User,
    }

    def __init__(self, data):
        """Constructor

        :data: a json object representing the object
        """

        self._data = data
        #  log.debug(json.dumps(data, indent=2))
        content_data = data[data['entityType']]
        self.type = content_data['type']
        try:
            self.content = self.type_map[self.type](content_data)
        except KeyError:
            log.warning("Unknown entity type: %s" % self.type)
            self.content = Generic(content_data)

        self.title = self.content.get_title()

    def get_html_content(self):
        return self.content.get_html_content()

    def get_title(self):
        return self.content.get_title()

    def get_columns(self):
        return self.content.get_columns()

    def get_head(self):
        return self.content.get_head()

    def match(self, search_string):
        return self.content.match(search_string)

    def get_content(self):
        # TODO load content if not in object already
        #  return self._data['content']['_expandable']['container']
        return self.content.get_content()

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)
