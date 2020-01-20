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

__help__ = """Confluence Feed

What you see here are items contained in a Confluence RSS feed. The type of
each item is indicated by a single letter:

    * P: Page
    * C: Comment
    * B: Blogpost

"""

from congruence.views import ConfluenceMainView, ConfluenceListBox,\
    ConfluenceSimpleListEntry, ConfluenceTreeListBox,\
    ConfluenceCardTreeWidget
from congruence.interface import make_request, html_to_text
from congruence.logging import log
from congruence.confluence import get_nested_content, get_id_from_url
from congruence.sql import connection, engine

from datetime import datetime as dt
import json
import re
from subprocess import Popen, PIPE

import sqlalchemy as db
from bs4 import BeautifulSoup
from dateutil.parser import parse as dtparse
import urwid


metadata = db.MetaData()
feed = db.Table(
    "feed", metadata,
    db.Column("URL", db.String(1024)),
    db.Column("id", db.String(256)),
    db.Column("data", db.String(256**2)),
    #  autoload=True,
    #  autload_with=engine,
)
metadata.create_all(engine)


def get_feed_entries(**kwargs):
    parsed_entries = get_from_db(kwargs["URL"])
    result = [ConfluenceFeedEntry(e) for e in parsed_entries]
    #  result = change_filter(result)
    return result


def update_feed_entries(**kwargs):
    response = make_request(kwargs["URL"])
    soup = BeautifulSoup(response.text, features="lxml")
    feed_entries = soup.findAll("entry")
    parsed_entries = [xml_to_dict(e) for e in feed_entries]

    store_in_db(kwargs["URL"], parsed_entries)


def store_in_db(url, entries):
    query = db.insert(feed)
    values_list = [{
        "URL": url,
        "id": e["id"],
        "data": json.dumps(e)
    } for e in entries]
    connection.execute(query, values_list)


def get_from_db(url):
    log.info("Accessing DB to get cached feed...")
    query = db.select([feed])
    ResultProxy = connection.execute(query)
    result = ResultProxy.fetchall()
    return [json.loads(e[2]) for e in result]


def xml_to_dict(soup):
    type = soup.find("id").text
    type = re.search(r",[0-9]+:([a-z]*)-", type).groups()[0]
    date = soup.find("dc:date").text
    date = dt.strptime(date, "%Y-%m-%dT%H:%M:%S%z")\
        .strftime("%Y-%m-%d %H:%M")

    data = {
        "author": soup.find("dc:creator").text,
        "content": soup.find("summary").text,
        "date": date,
        "updated": soup.find("updated").text,
        "published": soup.find("published").text,
        "id": soup.find("id").text,
        "title": soup.find("title").text,
        "url": soup.find("link")["href"],
        "type": type,
    }
    return data


class PluginView(ConfluenceMainView):
    def __init__(self, props={}):
        def body_builder():
            entries = get_feed_entries(**props)
            return ConfluenceListBox(entries)
        self.props = props
        if "DisplayName" in props:
            title = "Feed: %(DisplayName)s" % props
        else:
            title = "Feed"
        super().__init__(
            body_builder,
            title,
            help_string=__help__,
        )

    def reload(self):
        log.info("Updating feed '%s'..." % self.props["URL"])
        update_feed_entries(**self.props)
        self.__init__(props=self.props)


class ConfluenceFeedEntry(ConfluenceSimpleListEntry):
    def __init__(self, data):
        if data['type'] in ["page", "blogpost"]:
            view = PageView(data["url"])
        elif data['type'] == "comment":
            view = CommentView(data["url"], title_text=data["title"])

        #  name = "[%(type)s] %(title)s (%(author)s), %(date)s" % data
        name = [
            data["type"][0].upper(),
            data["author"],
            data["date"],
            data["title"],
        ]

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
