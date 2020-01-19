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

from congruence.views import ConfluenceMainView, ConfluenceListBox,\
    ConfluenceSimpleListEntry, ConfluenceTreeListBox, ConfluenceTreeWidget
from congruence.interface import make_request, html_to_text
from congruence.logging import log

from datetime import datetime as dt
import json
import re
from subprocess import Popen, PIPE

from bs4 import BeautifulSoup
from dateutil.parser import parse as dtparse
import urwid


def get_feed_entries(**kwargs):
    response = make_request(kwargs["URL"])
    soup = BeautifulSoup(response.text, features="lxml")
    feed_entries = soup.findAll("entry")
    result = [ConfluenceFeedEntry(s) for s in feed_entries]
    #  result = change_filter(result)
    return result


class PluginView(ConfluenceMainView):
    def __init__(self, props={}):
        def body_builder():
            entries = get_feed_entries(**props)
            return ConfluenceListBox(entries)
        super().__init__(body_builder, "Feed: %(DisplayName)s" % props)


class ConfluenceFeedEntry(ConfluenceSimpleListEntry):
    def __init__(self, data):
        type = data.find("id").text
        type = re.search(r",[0-9]+:([a-z]*)-", type).groups()[0]
        date = data.find("dc:date").text
        date = dt.strptime(date, "%Y-%m-%dT%H:%M:%S%z")\
            .strftime("%Y-%m-%d %H:%M")

        data = {
            "author": data.find("dc:creator").text,
            "content": data.find("summary").text,
            "date": date,
            "updated": data.find("updated").text,
            "published": data.find("published").text,
            "id": data.find("id").text,
            "title": data.find("title").text,
            "url": data.find("link")["href"],
            "type": type,
        }

        if type in ["page", "blogpost"]:
            view = PageView(data["url"])
        elif type == "comment":
            view = CommentView(data["url"], title_text=data["title"])

        name = "[%(type)s] %(title)s (%(author)s), %(date)s" % data

        super().__init__(name, view)


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


class CommentWidget(ConfluenceTreeWidget):
    indent_cols = 2

    def get_value(self):
        node = self.get_node().get_value()
        return list(node.values())[0]

    def get_display_text(self):
        node = self.get_value()
        if node["title"] == 'root':
            return "Comments"
        else:
            return "%(displayName)s, %(date)s" % node

    def get_display_body(self):
        node = self.get_node().get_value()
        node = list(node.values())[0]
        if node["title"] == 'root':
            return ""
        else:
            return "%(content)s" % node

    def load_inner_widget(self):
        """Build a multi-line widget with a header and a body"""

        icon = [self.unexpanded_icon, self.expanded_icon][self.expanded]
        header = urwid.Text(self.get_display_text())
        header = urwid.Columns([('fixed', 1, icon), header], dividechars=1)
        header = urwid.AttrWrap(header, 'head')
        if self.get_display_body():
            body = urwid.AttrWrap(urwid.Text(self.get_display_body()), 'body')
            widget = urwid.Pile([header, body])
        else:
            widget = header
        return widget

    def get_indented_widget(self):
        widget = self.get_inner_widget()
        indent_cols = self.get_indent_cols()
        return urwid.Padding(widget, width=('relative', 100), left=indent_cols)


class CommentTree(ConfluenceTreeListBox):
    def __init__(self, comments):
        self.comments = comments
        super().__init__(self.comments, CommentWidget)


def get_comments_of_page(id):
    def get_by_id(children, cid):
        for c in children:
            if cid in list(c.keys()):
                return c

    url = f"rest/api/content/{id}/child/comment?"\
          + "expand=body.view,content,version,ancestors"\
          + "&depth=all&limit=9999"
    r = make_request(url)
    comments = json.loads(r.text)["results"]
    result = []

    # Build the structure returned by Confluence into something more useful.
    # Most importantly, it's a flat list of all comments with each comment
    # possessing a list of its ancestors. We want a nested list.
    # Also, we only keep track of certain properties.
    for c in comments:
        parent = result
        # Step down the ancestor list
        if c["ancestors"]:
            for a in reversed(c["ancestors"]):
                parent = get_by_id(parent, a["id"])["children"]
        date = c["version"]["when"]
        date = dtparse(date).strftime("%Y-%m-%d %H:%M")

        parent.append({
            c["id"]: {
                "title": c["title"],
                "username": c["version"]["by"]["username"],
                "displayName": c["version"]["by"]["displayName"],
                "date": date,
                "content": html_to_text(c["body"]["view"]["value"]),
                # TODO insert selection of inline comments
            },
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
