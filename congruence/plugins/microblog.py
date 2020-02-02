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
from congruence.views.listbox import CongruenceListBox, CardListBoxEntry
from congruence.interface import make_request, html_to_text, convert_date
from congruence.logging import log
from congruence.objects import ContentObject

import urwid


class MicroblogView(CongruenceListBox):
    key_actions = ['load more']

    def __init__(self, properties={}):
        self.title = "Microblog"
        if 'limit' in properties['Parameters']:
            self.limit = properties['Parameters']['limit']
        else:
            self.limit = 20
        if 'replyLimit' in properties['Parameters']:
            self.replyLimit = properties['Parameters']['replyLimit']
        else:
            self.replyLimit = 999
        self.post_data = properties['Data']
        self.offset = 0

        self.entries = self.get_microblog()
        self.app.alert('Received %d items' % len(self.entries), 'info')
        super().__init__(self.entries, help_string=__help__)

    def ka_load_more(self, size=None):
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


class MicroblogEntry(CardListBoxEntry):
    """Represents microblog entries or replies to one entry as a list of
    widgets"""

    def __init__(self, obj, is_reply=False):
        self.obj = obj
        self.is_reply = is_reply
        super().__init__(self.obj)

    def get_next_view(self):
        if self.is_reply:
            return MicroblogReplyDetails(self.obj._data)
        return MicroblogReplyView(self.obj._data)


class MicroblogObject(ContentObject):
    def __init__(self, data):
        self._data = data

    def get_title(self, cols=False):
        liked_by = [u["userFullname"] for u in self._data["likingUsers"]]
        max_likes = 3
        if len(liked_by) > max_likes:
            liked_by = " Liked by %s and %d more" % (
                ", ".join(liked_by[:max_likes]),
                len(liked_by) - max_likes,
            )
        elif len(liked_by) > 0:
            liked_by = " Liked by " + ", ".join(liked_by[:max_likes])
        else:
            liked_by = ""
        # TODO process 'hasliked'
        title = "%s (%s)%s" % (
            self._data["authorFullName"],
            convert_date(self._data["creationDate"]),
            liked_by,
        )
        return title

    def get_content(self):
        text = self._data["renderedContent"]
        text = html_to_text(text).strip()
        return text


class MicroblogReplyView(CongruenceListBox):
    def __init__(self, entries):
        self.title = "Replies"
        self.entries = [MicroblogEntry(MicroblogObject(entries),
                                       is_reply=True)]
        self.entries += [MicroblogEntry(MicroblogObject(e), is_reply=True)
                         for e in entries["replies"]]
        super().__init__(self.entries, help_string=__help__)


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
