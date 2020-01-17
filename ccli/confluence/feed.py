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

from ccli.views import ConfluenceParentNode
from ccli.interface import make_request, html_to_text

from datetime import datetime as dt
import re

from bs4 import BeautifulSoup
import urwid


class ConfluenceFeedNode(ConfluenceParentNode):
    def __init__(self, data):
        self._data = data
        type = data.find("id").text
        type = re.search(r",[0-9]+:([a-z]*)-", type).groups()[0]
        date = data.find("dc:date").text
        date = dt.strptime(date, "%Y-%m-%dT%H:%M:%S%z")\
            .strftime("%Y-%m-%d %H:%M")

        self.data = {
            "author": data.find("dc:creator").text,
            "content": data.find("summary").text,
            "date": date,
            "updated": data.find("updated").text,
            "published": data.find("published").text,
            "id": data.find("id").text,
            "title": data.find("title").text,
            "url": data.find("summary").text,
            "type": type,
        }

        self.data["name"] = "[%(type)s] %(title)s (%(author)s), %(date)s" \
            % self.data
        self.data["children"] = []

    def view(self, app):
        return PageView(self["content"], app)


class PageView(urwid.Frame):
    def __init__(self, content, app):
        self.app = app
        text = html_to_text(content)
        self.body = urwid.Filler(urwid.Text(text))
        view = urwid.Frame(
            urwid.AttrWrap(self.body, 'body'),
        )
        super().__init__(view)

    def keypress(self, size, key):
        if key == "b":
            self.app.pop_view()
            return None
        return self.body.keypress(size, key)


def get_feed_entries(**kwargs):
    response = make_request(kwargs["URL"])
    soup = BeautifulSoup(response.text, features="lxml")
    feed_entries = soup.findAll("entry")
    result = [ConfluenceFeedNode(s) for s in feed_entries]
    #  result = change_filter(result)
    return result
