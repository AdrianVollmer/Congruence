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

__help__ = """Space View

This is a tree view of all pages in a space.

"""

from congruence.views import ConfluenceMainView, ConfluenceTreeListBox,\
        ConfluenceTreeWidget
from congruence.logging import log
from congruence.confluence import get_nested_content


# Can't get the full tree due to the way the Confluence API works. Must be
# loaded on expansion
def get_page_tree(name):
    def attr_picker(c):
        return {
            "title": c["title"],
        }
    log.info("Load page tree of space '%s'" % name)
    url = f"rest/api/space/{name}/content?depth=root"
    page_tree = get_nested_content(url, attr_picker)
    return page_tree


class PluginView(ConfluenceMainView):
    def __init__(self, props={}):
        def body_builder():
            entries = get_page_tree(props["Name"])
            return PageTree(entries)
        title = "Space: " + props["Name"]
        super().__init__(
            body_builder,
            title,
            help_string=__help__,
        )


class PageTree(ConfluenceTreeListBox):
    def __init__(self, comments):
        self.comments = comments
        super().__init__(self.comments, ConfluenceTreeWidget)
