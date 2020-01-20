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


from congruence.views import ConfluenceMainView, ConfluenceTreeListBox,\
        ConfluenceCardTreeWidget
from congruence.interface import make_request, html_to_text
from congruence.logging import log

import json
import re
from subprocess import Popen, PIPE

from dateutil.parser import parse as dtparse
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


class PageView(ConfluenceMainView):
    """Open a confluence page/blogpost in the external CLI browser"""

    def __init__(self, url, external=True):
        def body_builder():
            log.debug("Build HTML view for %s" % self.url)
            id = get_id_from_url(self.url)
            rest_url = f"rest/api/content/{id}?expand=body.storage"
            content = make_request(rest_url).text
            content = json.loads(content)
            content = content["body"]["storage"]["value"]

            if external:
                content = f"<html><head></head><body>{content}</body></html>"
                process = Popen("elinks", stdin=PIPE, stderr=PIPE)
                process.stdin.write(content.encode())
                process.communicate()
                return None
            else:
                content = f"<html><head></head><body>{content}</body></html>"
                text = html_to_text(content)
                return urwid.Frame(urwid.Filler(urwid.Text(text)))
        self.url = url
        super().__init__(body_builder)


class CommentView(ConfluenceMainView):
    """Display a comment tree

    url: URL to the Confluence page
    focused_comment_id: ID of the comment which gets the initial focus
    """

    def __init__(self, url, focused_comment_id=None, **kwargs):
        def body_builder():
            id = get_id_from_url(self.url)
            log.debug("Build CommentView for page with id '%s'" % id)
            comments = {
                "0": {"title": "root"},
                "children": get_comments_of_page(id),
            }
            #  TODO use focused_comment_id
            return CommentTree(comments)

        self.url = url
        self.focused_comment_id = re.search(r'#(.*)$', url).groups()[0]
        super().__init__(body_builder, **kwargs)


class CommentWidget(ConfluenceCardTreeWidget):
    def get_display_header(self):
        node = self.get_value()
        if node["title"] == 'root':
            return "Comments"
        else:
            return "%(displayName)s, %(date)s" % node


class CommentTree(ConfluenceTreeListBox):
    def __init__(self, comments):
        self.comments = comments
        super().__init__(self.comments, CommentWidget)


def get_comments_of_page(id):
    def attr_picker(c):
        date = c["version"]["when"]
        date = dtparse(date).strftime("%Y-%m-%d %H:%M")
        return {
            "title": c["title"],
            "username": c["version"]["by"]["username"],
            "displayName": c["version"]["by"]["displayName"],
            "date": date,
            "content": html_to_text(c["body"]["view"]["value"]),
            # TODO insert selection of inline comments
        }
    url = f"rest/api/content/{id}/child/comment?"\
          + "expand=body.view,content,version,ancestors"\
          + "&depth=all&limit=9999"
    return get_nested_content(url, attr_picker)
