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

from congruence.views.common import CongruenceTextBox, key_action
from congruence.views.listbox import CongruenceListBox, \
        ColumnListBoxEntry
from congruence.views.treelistbox import CongruenceTreeListBox,\
        CongruenceCardTreeWidget
from congruence.interface import make_request, convert_date
from congruence.tools import create_diff
from congruence.logging import log
from congruence.objects import Comment, ContentWrapper, post_comment
import congruence.strings as cs
from congruence.external import open_gui_browser, open_doc_in_cli_browser
import congruence.environment as env


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

    url = f'rest/api/content/{id}/child/comment'
    params = {
        'expand': 'body.view,content,history.lastUpdated,version,ancestors,'
                  'extensions.inlineProperties,version',
        'depth': 'all',
        'limit': 9999,
    }

    items = []
    while True:
        r = make_request(url, params=params)
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

    def __init__(self, page_id, obj, focus_id=None):
        self.title = "Comments"
        self.page = obj
        self.page_id = page_id
        log.debug("Build CommentContextView for comments of page with id '%s'"
                  % page_id)
        comments = {
            '0': {'title': obj.title, 'id': obj.id},
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

    @key_action
    def reply(self, size=None):
        obj = self.get_focus()[0].get_value()
        try:
            prev_msg = obj.get_content()
        except AttributeError:
            # It's the root object and thus we send a root comment
            prev_msg = ''
            obj = None
            help_text = ""
        else:
            prev_msg = prev_msg.splitlines()
            prev_msg = '\n'.join([f"## > {line}" for line in prev_msg])
            prev_msg = "## %s wrote:\n%s" % (obj.versionby.display_name,
                                             prev_msg)
            help_text = cs.REPLY_MSG + prev_msg
        reply = env.app.get_long_input(help_text)

        if not reply:
            env.app.alert("Reply empty, aborting", 'warning')
            return
        try:
            if obj:
                obj.send_reply(reply)
            else:
                post_comment(reply, self.page_id)
        except Exception:
            env.app.alert("Comment failed", 'error')
        else:
            env.app.alert("Comment sent", 'info')

        # TODO self.update()

    @key_action
    def like(self, size=None):
        comment = self.get_focus()[0].get_value()
        if comment.toggle_like():
            if comment.liked:
                env.app.alert("You liked this", 'info')
            else:
                env.app.alert("You unliked this", 'info')

    @key_action
    def cli_browser(self, size=None):
        obj = self.focus.get_value()
        try:
            id = obj.id
        except AttributeError:
            # The root object is just a dict, not an object
            id = obj['id']
        open_content_in_cli_browser(env.app, id)

    @key_action
    def gui_browser(self, size=None):
        obj = self.focus.get_value()
        url = obj.url
        open_gui_browser(url)


class SingleCommentView(CongruenceTextBox):
    """A text box showing metadata of a comment and the actual comment"""

    def __init__(self, obj):
        self.obj = obj
        self.title = "Comment"
        try:
            update = self.obj._data['version']
            infos = {
                'Title': obj.get_title(),
                'Last updated by': update['by']['displayName'],
                'Last updated at': convert_date(update['when']),
                'Last change message': update['message'],
                'Version number': update['number'],
            }
            text = '\n'.join([f'{k}: {v}' for k, v in infos.items()])
            text += '\n\n' + self.obj.get_content()
        except KeyError as e:
            env.app.alert("KeyError (%s), displaying raw data" % e, 'error')
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

    def __init__(self, obj):
        self.obj = obj
        self.title = "Page"
        if 'content' in obj._data:
            content = obj._data['content']
        else:
            content = obj._data
        # TODO don't access private member
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
            env.app.alert("KeyError (%s), displaying raw data" % e, 'error')
            text = obj.get_json()
        help_string = cs.PAGE_VIEW_HELP
        super().__init__(text, help_string=help_string)

    @key_action
    def list_diff(self, size=None):
        try:
            view = DiffView(self.obj.content.id)
            env.app.push_view(view)
        except KeyError:
            env.app.alert('No diff available', 'warning')

    @key_action
    def cli_browser(self, size=None):
        id = self.obj.content.id
        open_content_in_cli_browser(env.app, id)

    @key_action
    def gui_browser(self, size=None):
        id = self.obj.content.id
        url = f"pages/viewpage.action?pageId={id}"
        open_gui_browser(url)

    @key_action
    def go_to_comments(self, size=None):
        view = CommentContextView(self.obj.content.id, self.obj.content)
        env.app.push_view(view)

    @key_action
    def like(self, size=None):
        if self.obj.content.toggle_like():
            if self.obj.content.liked:
                env.app.alert("You liked this", 'info')
            else:
                env.app.alert("You unliked this", 'info')
        else:
            env.app.alert("Like failed", 'info')


class DiffView(CongruenceTextBox):
    def __init__(self, page_id, first=None, second=None):
        self.page_id = page_id
        self.title = "Diff"
        self.first = first
        self.second = second
        self.diff = self.get_diff()

        if not self.diff:
            self.diff = cs.DIFF_EMPTY
        help_string = cs.DIFF_VIEW_HELP
        super().__init__(self.diff, color=True, help_string=help_string)

    def get_diff(self):
        url = f'rest/api/content/{self.page_id}'
        params = {
            'expand': 'version,body.view'
        }
        # get first body
        if self.first:
            params['status'] = 'historical'
            params['version'] = self.first
        r = make_request(url, params=params)
        data = r.json()
        self.first = data['version']['number']
        version1 = data['body']['view']['value']
        tofile = "Version number %d by %s, %s" % (
            self.first,
            data['version']['by']['displayName'],
            convert_date(data['version']['when']),
        )

        # get second body
        if not self.second:
            self.second = self.first - 1
        params['version'] = self.second
        params['status'] = 'historical'

        r = make_request(url, params=params)
        data = r.json()
        version2 = data['body']['view']['value']
        fromfile = "Version number %d by %s, %s" % (
            self.second,
            data['version']['by']['displayName'],
            convert_date(data['version']['when']),
        )

        result = create_diff(version2,
                             version1,
                             fromfile=fromfile,
                             tofile=tofile,
                             html=True)
        return result

    @key_action
    def cycle_next(self, size=None):
        try:
            view = DiffView(self.page_id, self.first-1, self.second-1)
            env.app.pop_view()
            env.app.push_view(view)
        except KeyError:
            env.app.alert("No diff available", 'warning')

    @key_action
    def cycle_prev(self, size=None):
        try:
            view = DiffView(self.page_id, self.first+1, self.second+1)
            env.app.pop_view()
            env.app.push_view(view)
        except KeyError:
            env.app.alert("No diff available", 'warning')


class ContentList(CongruenceListBox):
    """A list box that can display Confluence content objects
    """

    def __init__(self, EntryClass=ColumnListBoxEntry, help_string=""):
        self.title = "Content"
        # TODO use factory for EntryClass
        self._entryclass = EntryClass
        self.params = {
            'cql': '',
            'start': 0,
            'limit': 20,
        }
        self.entries = []
        super().__init__(self.entries, help_string=help_string)

    @key_action
    def load_more(self, size=None):
        log.info("Load more ...")
        self.entries += self.get_entries()
        self.redraw()

    @key_action
    def load_much_more(self, size=None):
        log.info("Load much more ...")
        self.params["limit"] *= 5
        self.entries += self.get_entries()
        self.params["limit"] //= 5
        self.redraw()

    @key_action
    def update(self, size=None):
        log.info("Update ...")
        self.params["start"] = 0
        self.entries = self.get_entries()
        self.redraw()

    @key_action
    def cli_browser(self, size=None):
        node = self.get_focus()[0]
        id = node.obj.content.id
        open_content_in_cli_browser(env.app, id)

    @key_action
    def gui_browser(self, size=None):
        node = self.get_focus()[0]
        id = node.obj.content.id
        if not id:
            env.app.alert("Object has no ID", 'error')
            return
        url = f"pages/viewpage.action?pageId={id}"
        open_gui_browser(url)

    def get_entries(self):
        r = make_request(
            "rest/api/search",
            params=self.params
        )
        result = []
        response = r.json()
        if r.ok and response:
            for each in response['results']:
                obj = ContentWrapper(each)
                try:
                    if not getattr(obj.content, 'blacklisted', False):
                        result.append(self._entryclass(obj))
                except AttributeError:
                    result.append(self._entryclass(obj))

            #  result = change_filter(result)
            env.app.alert('Received %d items' % len(result), 'info')
            self.params["start"] += \
                self.params["limit"]
        return result


def open_content_in_cli_browser(app, id):
    log.debug("Build HTML view for page with id '%s'" % id)
    if not id:
        env.app.alert("Object has no ID", 'error')
        return
    rest_url = f"rest/api/content/{id}?expand=body.view"
    r = make_request(rest_url)
    if not r.ok:
        env.app.alert("Request failed (%d)" % r.status_code, 'error')
        return
    content = r.json()
    content = content["body"]["view"]["value"]

    content = f"<html><head></head><body>{content}</body></html>"
    open_doc_in_cli_browser(content.encode(), app)
