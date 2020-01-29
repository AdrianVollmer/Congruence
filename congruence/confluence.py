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
This file contains views and functions which are specific to Confluence
"""

from congruence.views.treelistbox import CongruenceTreeListBox,\
        CongruenceCardTreeWidget
from congruence.views.listbox import CongruenceListBox
from congruence.interface import make_request, convert_date
from congruence.logging import log
from congruence.objects import Comment
#  from congruence.external import open_gui_browser

import json
import re

import urwid


def get_comments_of_page(url):
    """Retrieve comments of a page from the Confluence API

    :id: the id of the page
    """
    def get_by_id(children, cid):
        for c in children:
            if cid in list(c.keys()):
                return c
    id = re.search('/([^/]*)$', url).groups()[0]
    log.debug("Get comment tree of page %s" % id)

    url = f"rest/api/content/{id}/child/comment?"\
          + "expand=body.view,content,version,ancestors"\
          + "&depth=all&limit=9999"

    items = []
    while True:
        r = make_request(url)
        parsed = json.loads(r.text)
        items += parsed["results"]
        links = parsed["_links"]
        if "next" in links:
            url = links["next"]
        else:
            break

    result = []

    # Build the structure returned by Confluence into something more useful.
    # Most importantly, it's a flat list of all items with each item
    # possessing a list of its ancestors. We want a nested list.
    # Also, we only keep track of certain attributes.
    for c in items:
        parent = result
        # Step down the ancestor list
        # ATTENTION: Apparently the order is arbitrary... can break
        for a in reversed(c["ancestors"]):
            parent = get_by_id(parent, a["id"])["children"]

        parent.append({
            c["id"]: Comment(c),
            "children": [],
        })

    return result


class CommentView(CongruenceTreeListBox):
    """Display a comment tree

    :obj: one object of type Comment of the comment tree
    """

    key_map = {
        'r': ("reply", "Reply to a comment"),
        'L': ("like", "Toggle your 'like' of a comment"),
    }

    def __init__(self, obj):
        self.title = "Comments"
        comment_id = obj.id
        log.debug("Build CommentView for comment with id '%s'" % comment_id)
        #  log.debug(obj._data)
        #  container = obj.get_content()
        #  page_id = re.search(r'/([^/]*$)', container).groups()[0]
        url = obj.get_parent_container()
        comments = {
            "0": {"title": "root"},
            "children": get_comments_of_page(url),
        }
        super().__init__(comments, CommentWidget)
        # set focus
        node = self._body.focus
        while True:
            node = self._body.get_next(node)[1]
            if not node:
                break
            if list(node.get_value().keys())[0] == comment_id:
                break
        if node:
            self.set_focus(node)

    def key_action(self, action, size=None):
        if action == "reply":
            obj = self.get_focus()[0].get_value()
            prev_msg = obj.get_content()
            prev_msg = prev_msg.splitlines()
            prev_msg = '\n'.join([f"## > {line}" for line in prev_msg])
            prev_msg = "## %s wrote:\n%s" % (obj.author, prev_msg)
            help_text = cs.REPLY_MSG + prev_msg
            reply = self.app.get_long_input(help_text)

            if reply:
                obj.send_reply(reply)

        elif action == "like":
            comment = self.get_focus()[0].get_value()
            if comment.toggle_like():
                if comment.liked:
                    self.app.alert('You liked this', 'info')
                else:
                    self.app.alert('You unliked this', 'info')
        else:
            super().key_action(action, size=size)


class CommentWidget(CongruenceCardTreeWidget):
    def get_next_view(self):
        pass


class CommentDetails(CongruenceListBox):
    def __init__(self, data):
        self.title = "Details"
        # Build details view
        #  del data['content']
        max_len = max([len(k) for k, _ in data.items()])
        line = [[urwid.Text(k), urwid.Text(str(v))] for k, v in data.items()]
        line = [urwid.Columns([(max_len + 1, k), v])
                for k, v in line]
        super().__init__(line)


class PageView(CongruenceListBox):
    def __init__(self, obj):
        self.title = "Page"
        #  text = [urwid.Text(obj.get_json())]
        update = obj._data["content"]["history"]["lastUpdated"]
        infos = {
            "Title": obj.get_title(),
            "Space": obj._data["content"]["space"]["key"],
            "Last updated by": update["by"]["displayName"],
            "Last updated at": convert_date(update["when"]),
            "Message": update["message"],
            "Version number": update["number"],
        }
        text = urwid.Text('\n'.join([f"{k}: {v}" for k, v in infos.items()]))
        super().__init__(urwid.SimpleFocusListWalker([text]))
