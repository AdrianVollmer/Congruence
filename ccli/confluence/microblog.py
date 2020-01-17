#  ccli: A command line interface to Confluence
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

from ccli.treeview import ConfluenceParentNode
from ccli.interface import make_request, html_to_text

import json

import urwid


class ConfluenceMicroblogNode(ConfluenceParentNode):
    def __init__(self, data):
        self.data = data
        self.data["children"] = []
        topic = self.data["topic"]["name"]
        self.data["name"] = (
            "%(authorFullName)s, "
            "%(friendlyFormattedCreationDate)s"
            f" [{topic}]"
        ) % self.data

    def view(self, app):
        entry_list = []
        for r in [self.data] + self.data["replies"]:
            entry_list.append(MicroblogEntry(r))
        return MicroblogList(entry_list, app)


class MicroblogList(urwid.Frame):
    def __init__(self, entry_list, app):
        self.app = app
        self.listbox = urwid.ListBox(urwid.SimpleFocusListWalker(entry_list))
        self.footer = urwid.AttrWrap(urwid.Text("Microblog"), 'foot')
        view = urwid.Frame(
            urwid.AttrWrap(self.listbox, 'body'),
            footer=self.footer
        )
        super().__init__(view)

    def keypress(self, size, key):
        if key == "b":
            self.app.pop_view()
            return None
        return self.listbox.keypress(size, key)


class MicroblogEntry(urwid.Pile):
    """Represents a microblog entry in a list of widgets"""

    def __init__(self, data):
        self.selected = False
        self.data = data
        widgets = [
            self.render_head(data),
            self.render_content(data),
        ]

        super().__init__(widgets)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == "x":
            raise Exception("x")
            return None
        return key

    def render_head(self, entry):
        import datetime as dt
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
            dt.datetime.fromtimestamp(entry["creationDate"]/1000.)
            .strftime("%Y-%m-%d %H:%M"),
            liked_by,
        )
        return urwid.AttrMap(
            urwid.Text(header),
            'head',
            focus_map='selected'
        )

    def render_content(self, entry):
        text = entry["renderedContent"]
        text = html_to_text(text)
        return urwid.AttrMap(urwid.Text(text), 'body')


def get_microblog():
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
    result = [ConfluenceMicroblogNode(s) for s in entries["microposts"]]
    return result
