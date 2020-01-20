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

from congruence.views import ConfluenceParentNode
from congruence.interface import make_request

import json


class ConfluenceSpace(ConfluenceParentNode):
    def __init__(self, data):
        self.data = data
        self.data["children"] = []

    def load_pages(self):
        response = make_request(
            "rest/refinedtheme/latest/space/CON/pagetree",
            params={"expandDepth": "9999"},
        )
        page_tree = json.loads(response.text)
        self.data["children"] = page_tree["pages"]

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
