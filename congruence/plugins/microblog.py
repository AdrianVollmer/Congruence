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
from congruence.views import CongruenceListBox, CongruenceListBoxEntry
from congruence.interface import make_request, html_to_text, convert_date
from congruence.logging import log

import json

import urwid


def get_microblog(properties):
    """Load Microblog entries via HTTP"""

    response = make_request(
        "rest/microblog/1.0/microposts/search",
        params={
            "offset": "0",
            "limit": "9999",
            "replyLimit": "9999"
        },
        data='thread.topicId:(12 OR 13 OR 14 OR 15 OR 16)',
        headers={
            "Content-Type": "application/json",
        },
    )
    entries = json.loads(response.text)
    #  log.debug(entries)
    result = []
    for e in entries['microposts']:
        result.append(MicroblogEntry(e))
    return result


class MicroblogView(CongruenceListBox):
    def __init__(self, properties={}):
        self.title = "Microblog"
        self.properties = properties
        self.entries = get_microblog(self.properties)
        #  self.title = title
        super().__init__(self.entries, help_string=__help__)


class MicroblogEntry(CongruenceListBoxEntry):
    """Represents microblog entries or replies to one entry as a list of
    widgets"""

    def __init__(self, data, is_reply=False):
        self.data = data
        key_map = {
            'enter': MicroblogReplyDetails if is_reply else MicroblogReplyView
        }
        super().__init__(
            self.data,
            CardListBoxEntry,
            key_map=key_map,
        )


class CardListBoxEntry(urwid.Pile):
    def __init__(self, data):
        self.data = data
        widgets = [
            self.render_head(self.data),
            self.render_content(self.data),
        ]
        super().__init__(widgets)

    def render_head(self, entry):
        liked_by = [u["userFullname"] for u in entry["likingUsers"]]
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
        header = "%s (%s)%s" % (
            entry["authorFullName"],
            convert_date(entry["creationDate"]),
            liked_by,
        )
        return urwid.AttrMap(
            urwid.Text(header),
            'card-head',
            focus_map='card-focus'
        )

    def render_content(self, entry):
        text = entry["renderedContent"]
        text = html_to_text(text).strip()
        return urwid.AttrMap(urwid.Text(text), 'body')


class MicroblogReplyView(CongruenceListBox):
    def __init__(self, entries):
        self.title = "Replies"
        self.entries = [MicroblogEntry(entries, is_reply=True)]
        self.entries += [MicroblogEntry(e, is_reply=True)
                         for e in entries["replies"]]
        log.debug(self.entries)
        super().__init__(self.entries, help_string=__help__)


class MicroblogReplyDetails(CongruenceListBox):
    def __init__(self, data):
        self.title = "Details"
        # Build details view
        log.debug(data)
        del data['renderedContent']
        max_len = max([len(k) for k, _ in data.items()])
        line = [[urwid.Text(k), urwid.Text(str(v))] for k, v in data.items()]
        line = [urwid.Columns([(max_len + 1, k), v])
                for k, v in line]
        super().__init__(line)


PluginView = MicroblogView
