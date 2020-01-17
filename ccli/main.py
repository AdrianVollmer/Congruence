from ccli.args import config
from ccli.treeview import ConfluenceApp
from ccli.interface import HOST
from ccli.confluence.feed import get_feed_entries
from ccli.confluence.spaces import get_spaces
from ccli.confluence.microblog import get_microblog


GET_ITEMS = {
    "Feed": get_feed_entries,
    "Microblog": get_microblog,
    "SpaceTree": get_spaces,
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
