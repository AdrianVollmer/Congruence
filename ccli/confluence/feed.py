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
from ccli.interface import make_request
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

        view = PageView(data["url"])
        name = "[%(type)s] %(title)s (%(author)s), %(date)s" % data

        super().__init__(name, view)


class PageView(ConfluenceMainView):
    def __init__(self, url):
        def body_builder():
            log.debug("Build HTML view for %s" % self.url)
            content = make_request(self.url).text
            if 'id="content"' in content:
                soup = BeautifulSoup(content, features="lxml")
                content = soup.find("article")
            content = f"<html><head></head><body>{content}</body></html>"
            process = Popen("elinks", stdin=PIPE, stderr=PIPE)
            process.stdin.write(content.encode())
            process.communicate()
            return None
        self.url = url
        super().__init__(body_builder)
