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

__help__ = """Congruence Microblog

Here you can see the latest entries of the microblog plugin.

"""
from congruence.views.listbox import CongruenceListBox, \
        CardedListBoxEntry
from congruence.views.common import CongruenceTextBox, key_action
from congruence.interface import make_request, html_to_text, convert_date,\
        md_to_html
from congruence.logging import log
from congruence.objects import Content, is_blacklisted_user
from congruence.external import open_gui_browser
import congruence.strings as cs

import urwid


class MicroblogView(CongruenceListBox):
    def __init__(self, properties={}):
        self.title = "Microblog"
        self.properties = properties
        self.update()
        super().__init__(self.entries, help_string=__help__)

    @key_action
    def update(self, size=None):
        if 'limit' in self.properties['Parameters']:
            self.limit = self.properties['Parameters']['limit']
        else:
            self.limit = 20
        if 'replyLimit' in self.properties['Parameters']:
            self.replyLimit = self.properties['Parameters']['replyLimit']
        else:
            self.replyLimit = 999
        self.post_data = self.properties['Data']
        self.offset = 0

        self.entries = self.get_microblog()
        self.app.alert('Received %d items' % len(self.entries), 'info')
        if hasattr(self, 'walker'):
            # this check is done because if update is called before
            # super.__init__ the object is not ready for redrawing yet
            self.redraw()

    @key_action
    def load_more(self, size=None):
        self.entries += self.get_microblog()
        self.redraw()

    def get_microblog(self):
        """Load Microblog entries via HTTP"""

        log.info("Fetch microblog...")
        response = make_request(
            "rest/microblog/1.0/microposts/search",
            params={
                "offset": self.offset,
                "limit": self.limit,
                "replyLimit": self.replyLimit,
            },
            method='POST',
            data=self.post_data,
            headers={
                "Content-Type": "application/json",
            },
        )
        entries = response.json()
        result = []
        for e in entries['microposts']:
            result.append(MicroblogEntry(MicroblogObject(e), is_reply=False))
        self.offset += len(result)
        return result

    @key_action
    def gui_browser(self, size=None):
        node = self.get_focus()[0]
        post_id = node.obj._data['id']
        url = f"plugins/micropost/view.action?postId={post_id}"
        open_gui_browser(url)

    @key_action
    def post_comment(self, size=None):
        # TODO refactor to reduce duplicate code
        # TODO let the user pick
        topic_id = 16

        post_id = send_sketch(topic_id)
        if not post_id:
            self.app.alert("Failed to send sketch", 'error')
            return

        help_text = cs.REPLY_MSG
        reply = self.app.get_long_input(help_text)
        if not reply:
            self.app.alert("Reply empty, aborting", 'warning')
            return
        reply = md_to_html(reply, url_encode='html')

        headers = {
            'X-Atlassian-Token': 'no-check',
            'Content-Type':
                'application/x-www-form-urlencoded; charset=UTF-8',
        }
        data = f"{reply}&topicId={topic_id}&spaceKey=~admin"
        url = f"rest/microblog/1.0/microposts/{post_id}"
        r = make_request(url, method='PUT', data=data,
                         headers=headers, no_token=True)

        if r.status_code == 200:
            self.app.alert("Microblog post sent", 'info')
        else:
            self.app.alert("Failed to send microblog post", 'error')


class MicroblogEntry(CardedListBoxEntry):
    """Represents microblog entries or replies to one entry as a list of
    widgets"""

    def __init__(self, obj, is_reply=False):
        self.obj = obj
        self.is_reply = is_reply
        super().__init__(self.obj)

    def get_next_view(self):
        if not self.is_reply:
            return MicroblogReplyView(self.obj._data)
        d = self.obj._data
        text = f"Author: {d['authorFullName']}\n"
        date = convert_date(d["lastModificationDate"])
        text += f"Date: {date}\n"
        likes = [u['userFullname'] for u in d['likingUsers']]
        text += "Likes: " + ', '.join(likes)
        view = CongruenceTextBox(text)
        view.title = "Post"
        return view

    def search_match(self, search_string):
        return self.obj.match(search_string)


class MicroblogObject(Content):
    def __init__(self, data):
        self._data = data
        self.blacklisted = is_blacklisted_user(self._data['authorName'])

    def get_title(self):
        like_number = len(self._data['likingUsers'])
        likes = ""
        if like_number > 0:
            if like_number == 1 and self._data['hasLiked']:
                likes = ' - You liked this'
            else:
                likes = " - %d likes" % like_number
                if self._data['hasLiked']:
                    likes += ", including you"
        replies = ""
        if self._data['replies']:
            replies = " - %d replies" % len(self._data['replies'])
        title = "%s (%s)%s%s" % (
            self._data["authorFullName"] if not self.blacklisted
                else "<blocked user>",
            convert_date(self._data["lastModificationDate"]),
            replies,
            likes,
        )
        return title

    def get_head(self):
        return self.get_title()

    def get_content(self):
        if self.blacklisted:
            return ""
        text = self._data["renderedContent"]
        text = html_to_text(text).strip()
        return text


def send_sketch(topic_id):
    """Gets a post ID for a new microblog entry"""

    headers = {
        'X-Atlassian-Token': 'no-check',
        'Content-Type':
            'application/x-www-form-urlencoded; charset=UTF-8',
    }
    data = f"topicId={topic_id}"
    url = f"rest/microblog/1.0/sketch"
    r = make_request(url, method='POST', data=data,
                     headers=headers, no_token=True)

    if not r.status_code == 200:
        return

    post_id = r.text
    return post_id


class MicroblogReplyView(CongruenceListBox):
    def __init__(self, entries):
        self.title = "Replies"
        self.entries = [MicroblogEntry(MicroblogObject(entries),
                                       is_reply=True)]
        self.entries += [MicroblogEntry(MicroblogObject(e), is_reply=True)
                         for e in entries["replies"]]
        super().__init__(self.entries, help_string=__help__)

    @key_action
    def like(self, size=None):
        obj = self.focus.obj
        post_id = obj._data['id']
        headers = {
            'X-Atlassian-Token': 'no-check',
        }
        url = f"rest/microblog/1.0/microposts/{post_id}/like"
        r = make_request(url, method='POST', headers=headers, no_token=True)
        if r.status_code == 200:
            if r.text == 'true':
                self.app.alert("You liked this", 'info')
            elif r.text == 'false':
                self.app.alert("You unliked this", 'info')
        else:
            self.app.alert("Like failed", 'error')

    @key_action
    def reply(self, size=None):
        obj = self.entries[0].obj
        author = obj._data['authorFullName']
        topic_id = obj._data['topic']['id']
        parent_id = obj._data['id']

        post_id = send_sketch(topic_id)
        if not post_id:
            self.app.alert("Failed to send sketch", 'error')
            return

        prev_msg = obj._data['renderedContent']
        prev_msg = prev_msg.splitlines()
        prev_msg = '\n'.join([f"## > {line}" for line in prev_msg])
        prev_msg = "## %s wrote:\n%s" % (author, prev_msg)

        help_text = cs.REPLY_MSG + prev_msg
        reply = self.app.get_long_input(help_text)
        if not reply:
            self.app.alert("Reply empty, aborting", 'warning')
            return
        reply = md_to_html(reply, url_encode='html')

        headers = {
            'X-Atlassian-Token': 'no-check',
            'Content-Type':
                'application/x-www-form-urlencoded; charset=UTF-8',
        }
        data = f"{reply}&parentId={parent_id}&spaceKey=~admin"
        url = f"rest/microblog/1.0/microposts/{post_id}"
        r = make_request(url, method='PUT', data=data,
                         headers=headers, no_token=True)

        if r.status_code == 200:
            self.app.alert("Reply sent", 'info')
        else:
            self.app.alert("Failed to send reply", 'error')

    @key_action
    def gui_browser(self, size=None):
        obj = self.entries[0].obj
        post_id = obj._data['id']
        url = f"plugins/micropost/view.action?postId={post_id}"
        open_gui_browser(url)


class MicroblogPost(CongruenceTextBox):
    def __init__(self, data):
        self.title = "Post"
        max_len = max([len(k) for k, _ in data.items()])
        line = [[urwid.Text(k), urwid.Text(str(v))]
                for k, v in data.items()
                if not k == "renderedContent"]
        line = [urwid.Columns([(max_len + 1, k), v])
                for k, v in line]
        super().__init__(line)


class MicroblogReplyDetails(CongruenceListBox):
    def __init__(self, data):
        self.title = "Details"
        # Build details view
        max_len = max([len(k) for k, _ in data.items()])
        line = [[urwid.Text(k), urwid.Text(str(v))]
                for k, v in data.items()
                if not k == "renderedContent"]
        line = [urwid.Columns([(max_len + 1, k), v])
                for k, v in line]
        super().__init__(line)


PluginView = MicroblogView
