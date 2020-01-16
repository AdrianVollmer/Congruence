from ccli.treeview import ConfluenceTree


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
                "children": [],
            },
        ]
    }
    ConfluenceTree(content).main()
