from ccli.treeview import ConfluenceTree
from ccli.interface import authenticate_session
from ccli.confluence.spaces import get_spaces
from subprocess import check_output
from shlex import split


def get_example_tree():
    """ generate a quick 100 leaf tree for demo purposes """
    retval = {"name": "parent", "children": []}
    for i in range(10):
        retval['children'].append({"name": "child " + str(i)})
        retval['children'][i]['children'] = []
        for j in range(10):
            retval['children'][i]['children'].append({"name": "grandchild " +
                                                      str(i) + "." + str(j)})
    return retval


def main():
    #  sample = get_example_tree()
    pw = check_output(split("pass show ad"))[:-1].decode()
    authenticate_session("avollmer", pw)
    spaces = get_spaces()
    content = {
        "name": "root",
        "children": [
            {
                "name": "Latest changes",
                "children": [],
            },
            {
                "name": "Microblog",
                "children": [],
            },
            {
                "name": "Spaces",
                "children": spaces,
            },
        ]
    }
    ConfluenceTree(content).main()
