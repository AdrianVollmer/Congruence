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
#  GNU General Public License for more details.  #
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This file contains views and functions which are specific to Confluence
"""

from congruence.views.common import CongruenceTextBox
from congruence.views.treelistbox import CongruenceTreeListBox,\
        CongruenceCardTreeWidget
from congruence.interface import make_request, convert_date, html_to_text
from congruence.tools import create_diff
from congruence.logging import log
from congruence.objects import Comment
import congruence.strings as cs
from congruence.external import open_gui_browser, open_doc_in_cli_browser


def get_comments_of_page(id):
    """Retrieve comments of a page from the Confluence API

    :id: the id of the page
    """
    def get_by_id(children, cid):
        for c in children:
            if cid in list(c.keys()):
                return c
    #  id = re.search('/([^/]*)$', url).groups()[0]
    log.debug("Get comment tree of page %s" % id)

    url = f'rest/api/content/{id}/child/comment?'\
          + 'expand=body.view,content,version,ancestors'\
          + '&depth=all&limit=9999'

    items = []
    while True:
        r = make_request(url)
        parsed = r.json()
        items += parsed['results']
        links = parsed['_links']
        if 'next' in links:
            url = links['next']
        else:
            break

    result = []

    # Build the structure returned by Confluence into something more useful.
    # Most importantly, it's a flat list of all items with each item
    # possessing a list of its ancestors. We want a nested list.
    # Also, we only keep track of certain attributes.
    for c in items:
        parent = result
        # Step down the ancestor list
        # ATTENTION: Apparently the order is arbitrary... can break
        for a in reversed(c['ancestors']):
            parent = get_by_id(parent, a['id'])['children']

        parent.append({
            c['id']: Comment(c),
            'children': [],
        })

    #  log.debug(result)
    return result


class CommentContextView(CongruenceTreeListBox):
    """Display a comment tree

    :obj: one object of type Comment of the comment tree
    """

    key_actions = [
        'reply',
        'like',
        'cli browser',
        'gui browser',
        'toggle collapse',
    ]

    def __init__(self, page_id, title, focus_id=None):
        self.title = "Comments"
        #  comment_id = obj.id
        log.debug("Build CommentContextView for comments of page with id '%s'"
                  % page_id)
        #  url = obj.get_parent_container()
        #  title = obj._data['resultParentContainer']['title']
        comments = {
            '0': {'title': title},
            'children': get_comments_of_page(page_id),
        }
        help_string = cs.COMMENT_CONTEXT_VIEW_HELP
        super().__init__(comments, CommentWidget, help_string=help_string)
        # set focus
        if not focus_id:
            return
        node = self._body.focus
        while True:
            node = self._body.get_next(node)[1]
            if not node:
                break
            if list(node.get_value().keys())[0] == focus_id:
                break
        if node:
            self.set_focus(node)

    def ka_reply(self, size=None):
        obj = self.get_focus()[0].get_value()
        prev_msg = obj.get_content()
        prev_msg = prev_msg.splitlines()
        prev_msg = '\n'.join([f"## > {line}" for line in prev_msg])
        prev_msg = "## %s wrote:\n%s" % (obj.author, prev_msg)
        help_text = cs.REPLY_MSG + prev_msg
        reply = self.app.get_long_input(help_text)

        if reply:
            if obj.send_reply(reply):
                self.app.alert("Comment sent", 'info')
            else:
                self.app.alert("Comment failed", 'error')
        # TODO self.update()

    def ka_like(self, size=None):
        comment = self.get_focus()[0].get_value()
        if comment.toggle_like():
            if comment.liked:
                self.app.alert("You liked this", 'info')
            else:
                self.app.alert("You unliked this", 'info')

    def ka_cli_browser(self, size=None):
        obj = self.focus.get_value()
        id = obj.id
        log.debug("Build HTML view for page with id '%s'" % id)
        rest_url = f"rest/api/content/{id}?expand=body.storage"
        r = make_request(rest_url)
        content = r.json()
        content = content['body']['storage']['value']

        content = f'<html><head></head><body>{content}</body></html>'
        open_doc_in_cli_browser(content.encode(), self.app)

    def ka_gui_browser(self, size=None):
        obj = self.focus.get_value()
        url = obj._data['_links']['webui']
        open_gui_browser(url)


class SingleCommentView(CongruenceTextBox):
    """A text box showing metadata of a comment and the actual comment"""

    def __init__(self, obj):
        self.obj = obj
        self.title = "Comment"
        content = obj._data
        try:
            update = content['version']
            infos = {
                'Title': obj.get_title(),
                #  'Space': content['space']['name'],
                #  'Space key': content['space']['key'],
                #  'Created by': history['createdBy']['displayName'],
                #  'Created at': convert_date(history['createdDate']),
                'Last updated by': update['by']['displayName'],
                'Last updated at': convert_date(update['when']),
                'Last change message': update['message'],
                'Version number': update['number'],
            }
            text = '\n'.join([f'{k}: {v}' for k, v in infos.items()])
            text += '\n\n' + html_to_text(self.obj.get_content())
        except KeyError as e:
            self.app.alert("KeyError (%s), displaying raw data" % e, 'error')
            text = obj.get_json()
        help_string = cs.COMMENT_VIEW_HELP
        super().__init__(text, help_string=help_string)


class CommentWidget(CongruenceCardTreeWidget):
    def __init__(self, node):
        self.obj = list(node.get_value().values())[0]
        super().__init__(node)

    def get_next_view(self):
        if isinstance(self.obj, dict):
            # It's the root node
            return None
        view = SingleCommentView(self.obj)
        return view


class PageView(CongruenceTextBox):
    """A text box showing metadata of a page"""

    key_actions = [
        'list diff',
        'cli browser',
        'gui browser',
        'go to comments',
    ]

    def __init__(self, obj):
        self.obj = obj
        self.title = "Page"
        #  text = [urwid.Text(obj.get_json())]
        if 'content' in obj._data:
            content = obj._data['content']
        else:
            content = obj._data
        try:
            history = content['history']
            update = history['lastUpdated']
            infos = {
                'Title': obj.get_title(),
                'Space': content['space']['name'],
                'Space key': content['space']['key'],
                'Created by': history['createdBy']['displayName'],
                'Created at': convert_date(history['createdDate']),
                'Last updated by': update['by']['displayName'],
                'Last updated at': convert_date(update['when']),
                'Last change message': update['message'],
                'Version number': update['number'],
            }
            text = '\n'.join([f'{k}: {v}' for k, v in infos.items()])
        except KeyError as e:
            self.app.alert("KeyError (%s), displaying raw data" % e, 'error')
            text = obj.get_json()
        help_string = cs.PAGE_VIEW_HELP
        super().__init__(text, help_string=help_string)

    def ka_list_diff(self, size=None):
        try:
            view = DiffView(self.obj.id)
            self.app.push_view(view)
        except KeyError:
            self.app.alert('No diff available', 'warning')

    def ka_cli_browser(self, size=None):
        id = self.obj.id
        log.debug("Build HTML view for page with id '%s'" % id)
        rest_url = f"rest/api/content/{id}?expand=body.storage"
        r = make_request(rest_url)
        content = r.json()
        content = content["body"]["storage"]["value"]

        content = f"<html><head></head><body>{content}</body></html>"
        open_doc_in_cli_browser(content.encode(), self.app)

    def ka_gui_browser(self, size=None):
        id = self.obj.id
        url = f"pages/viewpage.action?pageId={id}"
        open_gui_browser(url)

    def ka_go_to_comments(self, size=None):
        page_id = self.obj.id
        title = self.obj.title
        view = CommentContextView(page_id, title)
        self.app.push_view(view)


class DiffView(CongruenceTextBox):
    key_actions = ['cycle next', 'cycle prev']

    def __init__(self, page_id, first=None, second=None):
        self.page_id = page_id
        self.title = "Diff"
        url = f'rest/api/content/{page_id}'
        params = {
            'expand': 'version,body.view'
        }
        # get first body
        if first:
            self.first = first
            params['status'] = 'historical'
            params['version'] = first
        r = make_request(url, params=params)
        data = r.json()
        self.first = data['version']['number']
        self.version1 = data['body']['view']['value']
        tofile = "Version number %d by %s, %s" % (
            self.first,
            data['version']['by']['displayName'],
            convert_date(data['version']['when']),
        )

        # get second body
        if not second:
            self.second = self.first - 1
        else:
            self.second = second
        params['version'] = self.second
        params['status'] = 'historical'

        r = make_request(url, params=params)
        data = r.json()
        self.version2 = data['body']['view']['value']
        fromfile = "Version number %d by %s, %s" % (
            self.second,
            data['version']['by']['displayName'],
            convert_date(data['version']['when']),
        )

        self.diff = create_diff(self.version2,
                                self.version1,
                                fromfile=fromfile,
                                tofile=tofile,
                                html=True)

        if not self.diff:
            self.diff = cs.DIFF_EMPTY
        help_string = cs.DIFF_VIEW_HELP
        super().__init__(self.diff, color=True, help_string=help_string)

    def ka_cycle_next(self, size=None):
        try:
            view = DiffView(self.page_id, self.first-1, self.second-1)
            self.app.pop_view()
            self.app.push_view(view)
        except KeyError:
            self.app.alert("No diff available", 'warning')

    def ka_cycle_prev(self, size=None):
        try:
            view = DiffView(self.page_id, self.first+1, self.second+1)
            self.app.pop_view()
            self.app.push_view(view)
        except KeyError:
            self.app.alert("No diff available", 'warning')
