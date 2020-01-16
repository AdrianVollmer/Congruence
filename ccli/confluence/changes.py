from ccli.treeview import ConfluenceParentNode
from ccli.interface import make_request

from bs4 import BeautifulSoup


class ConfluenceChange(ConfluenceParentNode):
    def __init__(self, data):
        self._data = data
        self.data = {
            "author": data.find("dc:creator").text,
            "content": data.find("summary").text,
            "date": data.find("dc:date").text,
            "updated": data.find("updated").text,
            "published": data.find("published").text,
            "id": data.find("id").text,
            "title": data.find("title").text,
            "url": data.find("summary").text,
        }

        self.data["name"] = "%(title)s (%(author)s)" % self.data
        self.data["children"] = []

    def __dict__(self):
        return self.data

    def __iter__(self):
        yield from self.data

    def __getitem__(self, item):
        return self.data[item]


def get_changes():
    response = make_request(
        "createrssfeed.action",
        params={
            "types": ["page", "blogposts"],
            "pageSubTypes": ["comment", "attachment"],
            "blogpostSubTypes": ["comment", "attachment"],
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
        },
    )
    soup = BeautifulSoup(response.text, features="lxml")
    changes = soup.findAll("entry")
    result = [ConfluenceChange(s) for s in changes]
    return result
