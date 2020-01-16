from ccli.args import config
from ccli.treeview import ConfluenceTree
from ccli.interface import authenticate_session, HOST
from ccli.confluence.spaces import get_spaces
from ccli.confluence.microblog import get_microblog
from subprocess import check_output
from shlex import split


def main():
    user = config["Username"]
    pw = check_output(split(config["Password_Command"]))[:-1].decode()
    authenticate_session(user, pw)
    microblog = get_microblog()
    #  print(microblog)
    #  exit(0)
    spaces = get_spaces()

    content = {
        "name": "Confluence (%s)" % HOST,
        "children": [
            {
                "name": "Latest changes",
                "children": [],
            },
            {
                "name": "Microblog",
                "children": microblog,
            },
            {
                "name": "Spaces",
                "children": spaces,
            },
        ]
    }
    ConfluenceTree(content).main()
