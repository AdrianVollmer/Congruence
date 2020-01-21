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
    ConfluenceSimpleListEntry
from congruence.interface import make_request
from congruence.logging import log
from congruence.confluence import PageView, CommentView
from congruence.sql import connection, engine

from datetime import datetime as dt
import json
import re

import sqlalchemy as db
from bs4 import BeautifulSoup


metadata = db.MetaData()
feed = db.Table(
    "feed", metadata,
    db.Column("URL", db.String(1024)),
    db.Column("id", db.String(256)),
    db.Column("read", db.Boolean(), default=False),
    db.Column("data", db.String(256**2)),
)
metadata.create_all(engine)


def get_feed_entries(**kwargs):
    """Load feed entries from database"""

    parsed_entries = get_from_db(kwargs["URL"])
    result = [ConfluenceFeedEntry(e) for e in parsed_entries]
    #  result = change_filter(result)
    return result


def update_feed_entries(**kwargs):
    """Request the feed over the network"""

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
    if values_list:
        connection.execute(query, values_list)


def get_from_db(url):
    log.info("Accessing DB to get cached feed...")
    query = db.select([feed])
    ResultProxy = connection.execute(query)
    ans = ResultProxy.fetchall()
    result = []
    for e in ans:
        try:
            result.append(json.loads(e[3]))
        except TypeError:
            log.error("Could not parse DB entry: %s" % e[3])
    return result


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


class FeedView(ConfluenceMainView):
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


PluginView = FeedView
