from ccli.treeview import ConfluenceParentNode
from ccli.interface import make_request
import json


class ConfluenceMicroblog(ConfluenceParentNode):
    def __init__(self, data):
        self.data = data
        self.data["children"] = []
        topic = self.data["topic"]["name"]
        self.data["name"] = (
            "%(authorFullName)s, "
            "%(friendlyFormattedCreationDate)s"
            f" [{topic}]"
        ) % self.data

    def __iter__(self):
        yield from self.data

    def __getitem__(self, item):
        return self.data[item]


def get_microblog():
    response = make_request(
        "rest/microblog/1.0/microposts/search",
        params={
            "offset": "0",
            "limit": "20",
            "replyLimit": "3"
        },
        data='thread.topicId:(12 OR 13 OR 14 OR 15 OR 16)',
        headers={
            "Content-Type": "application/json",
        },
    )
    entries = json.loads(response.text)
    result = [ConfluenceMicroblog(s) for s in entries["microposts"]]
    return result
