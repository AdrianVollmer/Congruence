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
from congruence.interface import make_request, html_to_text, convert_date
from congruence.logging import log
#  from congruence.external import open_gui_browser

import json
import re

import urwid


def get_nested_content(url, attr_picker):
    """Retrieve content from the Confluence API

    url: the REST endpoint to use.
    attr_picker: a function that takes a dictionary and returns a
        different (e.g. a condensend one) dictionary.
    """
    def get_by_id(children, cid):
        for c in children:
            if cid in list(c.keys()):
                return c

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
            c["id"]: attr_picker(c),
            "children": [],
        })

    return result


def get_id_from_url(url):
    log.debug("Get pageId of %s" % url)
    m = re.search(r'pageId=([0-9]*)', url)
    if m:
        return m.groups()[0]
    m = re.search(r'display/([^/]+)(.*)/([^/]*)', url.split("?")[0])
    if not m:
        return None
    space, date, title = m.groups()[:3]
    type = "blogpost" if date else "page"
    log.debug(f"Getting id of '{space}/{title}', type '{type}'")
    # Better leave it all URL encoded
    r = make_request("rest/api/content?"
                     + f"type={type}&title={title}&spaceKey={space}")
    j = json.loads(r.text)
    if j["results"]:
        return j["results"][0]["id"]
    return None


class CommentView(CongruenceTreeListBox):
    """Display a comment tree

    :obj: one object of type Comment of the comment tree
    """

    key_map = {
        'r': ("reply", "Reply to a comment"),
        'l': ("like", "Toggle your 'like' of a comment"),
    }

    def __init__(self, obj):
        self.title = "Comments"
        comment_id = obj.id
        log.debug("Build CommentView for page with id '%s'" % comment_id)
        container = obj.get_content()
        page_id = re.search(r'/([^/]*$)', container).groups()[0]
        comments = {
            "0": {"title": "root"},
            "children": get_comments_of_page(page_id),
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
            reply = self.app.get_long_input("test")
            log.debug(reply)
            #  send_reply(reply)
        elif action == "like":
            self.load_much_more()
        else:
            super().key_action(action, size=size)


class CommentWidget(CongruenceCardTreeWidget):
    def get_next_view(self):
        pass


class CommentDetails(CongruenceListBox):
    def __init__(self, data):
        self.title = "Details"
        # Build details view
        del data['content']
        max_len = max([len(k) for k, _ in data.items()])
        line = [[urwid.Text(k), urwid.Text(str(v))] for k, v in data.items()]
        line = [urwid.Columns([(max_len + 1, k), v])
                for k, v in line]
        super().__init__(line)


def get_comments_of_page(id):
    def attr_picker(c):
        date = c["version"]["when"]
        date = convert_date(date)
        title = "%s, %s" % (
            c["version"]["by"]["displayName"],
            date,
        )
        return {
            "title": title,
            "username": c["version"]["by"]["username"],
            "displayName": c["version"]["by"]["displayName"],
            "date": date,
            "url": c["_links"]["webui"],
            "versions": str(c["version"]["number"]),
            "content": html_to_text(c["body"]["view"]["value"]),
            # TODO insert selection of inline comments
        }
    url = f"rest/api/content/{id}/child/comment?"\
          + "expand=body.view,content,version,ancestors"\
          + "&depth=all&limit=9999"
    return get_nested_content(url, attr_picker)
    # Likes can be retrieved like so (might be unstable):
    # https://confluence.syss.intern/rest/likes/1.0/content/31424614/likes
