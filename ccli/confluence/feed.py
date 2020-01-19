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

from ccli.views import ConfluenceMainView, ConfluenceListBox,\
    ConfluenceSimpleListEntry
from ccli.interface import make_request, html_to_text
from ccli.logging import log

from datetime import datetime as dt
import re
from subprocess import Popen, PIPE

from bs4 import BeautifulSoup
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
            view = CommentView(data["url"])

        name = "[%(type)s] %(title)s (%(author)s), %(date)s" % data

        super().__init__(name, view)


class PageView(ConfluenceMainView):
    """Open a confluence page/blogpost in the external CLI browser"""

    def __init__(self, url, external=True):
        def body_builder():
            log.debug("Build HTML view for %s" % self.url)
            # TODO use REST API
            content = make_request(self.url).text
            soup = BeautifulSoup(content, features="lxml")
            content = soup.find("article")

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
    def __init__(self, url, comment_id=None):
        def body_builder():
            log.debug("Build CommentView for %s" % self.url)
            content = make_request(self.url).text
            soup = BeautifulSoup(content, features="lxml")
            all_comments = soup.find(id="page-comments")
            all_comments = soup_to_dict(all_comments)
            log.debug(all_comments)

            # TODO build tree view of comments and focus on the current
            # comment
            return urwid.Frame(urwid.Filler(urwid.Text(text)))

        self.url = url
        comment_id = re.search(r'#(.*)$', url).groups()[0]
        super().__init__(body_builder)


def soup_to_dict(soup):
    result = []
    if not soup:
        return result
    comments = soup.find_all("li", class_="comment-thread")
    for c in comments:
        # TODO: Get likes
        comment = {
            "date": c.find("li", class_="comment-date").find("a")["title"],
            "author": c.find("h4", class_="author").find("a").text.strip(),
            #  "likedBy": likedBy,
            "body": str(c.find("div", class_="comment-content").contents[1]),
            "id": c.find("div", class_="comment")["id"],
            "children": soup_to_dict(c.find("ol", class_="comment-threads")),
        }
        comment["reply-url"] = c.find(id="reply-" + comment["id"])["href"]

        result.append(comment)

    return result
