from ccli.treeview import ConfluenceParentNode
from ccli.interface import make_request, html_to_text

from datetime import datetime as dt
import re

from bs4 import BeautifulSoup
import urwid


class ConfluenceChangeNode(ConfluenceParentNode):
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

    def __iter__(self):
        yield from self.data

    def __getitem__(self, item):
        return self.data[item]

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


def get_changes():
    from urllib3._collections import HTTPHeaderDict
    data = HTTPHeaderDict({
        "types": "page",
        "pageSubTypes": "comment",
        "blogpostSubTypes": "comment",
        "spaces": "conf_all",
        "title": "Confluence+RSS+Feed",
        "labelString": "",
        "excludedSpaceKeys": "",
        "sort": "modified",
        "maxResults": "20",
        "timeSpan": "5",
        "showContent": "true",
        "confirm": "Create+RSS+Feed",
        "os_authType": "basic",
    })
    # This is done so we can have a parameter twice
    data.add('types', 'blogpost')
    response = make_request(
        "createrssfeed.action",
        data=data,
    )
    soup = BeautifulSoup(response.text, features="lxml")
    changes = soup.findAll("entry")
    result = [ConfluenceChangeNode(s) for s in changes]
    #  result = change_filter(result)
    return result
