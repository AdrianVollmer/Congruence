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

from ccli.args import config
from ccli.treeview import ConfluenceApp
from ccli.interface import HOST
from ccli.confluence.feed import get_feed_entries
from ccli.confluence.spaces import get_spaces
from ccli.confluence.microblog import get_microblog
from ccli.confluence.notifications import get_notifications


GET_ITEMS = {
    "Feed": get_feed_entries,
    "Microblog": get_microblog,
    "SpaceTree": get_spaces,
    "Notifications": get_notifications,
    #  "Space": None,
}


def main():
    content = {
        "name": "Confluence (%s)" % HOST,
        "children": [],
    }
    for name, plugin in config["Plugins"].items():
        if not plugin:
            plugin = {}
        items = GET_ITEMS[name](**plugin)
        if plugin and "DisplayName" in plugin:
            name = plugin["DisplayName"]
        content["children"].append({"name": name, "children": items})

    ConfluenceApp(content).main()
