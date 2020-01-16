from ccli.treeview import ConfluenceParentNode
from ccli.interface import make_request
import json


class ConfluenceSpace(ConfluenceParentNode):
    def __init__(self, data):
        self.data = data
        self.data["name"] = data["title"]
        self.url = data["url"]
        self.data["children"] = []

    def __dict__(self):
        return self.data

    def __iter__(self):
        yield from self.data

    def __getitem__(self, item):
        return self.data[item]


def get_spaces():
    response = make_request(
        "rest/refinedtheme/latest/category/ab/",
        params={
            "include-children": "true",
            "recursive": "true",
            "exclude-links": "false",
            "simple-version": "false",
            "exclude-archived-spaces": "false",
        },
    )
    spaces = json.loads(response.text)
    result = [ConfluenceSpace(s) for s in spaces["children"]]
    return result
