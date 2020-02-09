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


__help__ = """Confluence Explorer

Expand items with the 'toggle collapse' key. They will dynamically retrieve
more content.
"""


from congruence.views.common import CongruenceTextBox
from congruence.views.treelistbox import CongruenceTreeListBox, \
    CongruenceTreeListBoxEntry
from congruence.interface import make_request
from congruence.external import open_gui_browser, open_doc_in_cli_browser
from congruence.logging import log
from congruence.confluence import CommentContextView, PageView
from congruence.objects import Space, Page

import urwid


class SpaceView(CongruenceTreeListBox):

    key_actions = [
        'toggle collapse',
        'cli browser',
        'gui browser',
    ]

    def __init__(self, properties={}):
        self.title = "Explorer"
        self.properties = properties
        url = 'rest/spacedirectory/1/search'
        params = {
            'query': '',
            'type': 'global',
            'status': 'current',
            'startIndex': '0',
        }
        headers = {
             'Accept': 'application/json',
        }
        self.spaces = []
        while True:
            r = make_request(url, params=params, headers=headers)
            j = r.json()
            self.spaces += j['spaces']
            size = j['totalSize']
            if len(self.spaces) >= size:
                break
            params['startIndex'] = len(self.spaces)
        self.entries = [{s['key']: ExpandableSpace({'space': s}),
                         'children': []}
                        for s in self.spaces]
        self.entries = {
            'Space Directory': {'title': 'Space Directory'},
            'children': self.entries,
        }
        super().__init__(self.entries, SpaceEntry, help_string=__help__)

    def ka_toggle_collapse(self, size=None):
        if self.focus.expanded:
            urwid.TreeListBox.keypress(self, size, '-')
        else:
            obj = self.focus.get_value()
            if not getattr(obj, 'expanded', True):
                new_children = obj.get_children()
                self.focus.add_children(new_children)
                obj.expanded = True
            urwid.TreeListBox.keypress(self, size, '+')

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
        try:
            url = obj._data['space']['link'][1]['href']
        except KeyError:
            url = obj._data['_links']['webui']
        open_gui_browser(url)

    def ka_show_details(self, size=None):
        obj = self.focus
        view = obj.get_details_view()
        if view:
            view.title = "Details"
            self.app.push_view(view)
        else:
            self.app.alert("Looks like this item has no details",
                           'warning')


class ExpandableSpace(Space):
    """This class can 'expand', i.e. load a list of pages in its space"""

    def __init__(self, data):
        super().__init__(data)
        self.expanded = False

    def get_children(self):
        self.expanded = True
        log.debug("Load descendants of %s..." % self.key)
        url = f'rest/api/space/{self.key}/content'
        params = {
            'depth': 'root',
            'expand': 'body,version,history.lastUpdated,space',
        }
        result = []
        while True:
            r = make_request(url, params=params)
            j = r.json()
            result += j['page']['results']
            size = j['page']['size']
            if len(result) >= size:
                break
            params['startIndex'] = len(result)
        result = [ExpandablePage(p) for p in result]
        log.debug("Retrieved %d items" % len(result))
        return result


class SpaceEntry(CongruenceTreeListBoxEntry):
    def __init__(self, node):
        self.node = node
        super().__init__(self.node)
        self.expanded = (not self.node.get_value()['children'] == [])
        self.update_expanded_icon()

    def get_next_view(self):
        obj = self.get_value()
        if obj.type in ["page", "blogpost"]:
            return PageView(obj)
        elif obj.type == "comment":
            return CommentContextView(obj)

    def get_details_view(self):
        text = self.get_value().get_json()
        return CongruenceTextBox(text)

    def search_match(self, search_string):
        return self.obj.match(search_string)

    def add_children(self, children):
        for c in children:
            # object can be space or page, so use key or id
            id = getattr(c, 'key', c.id)
            self.node.get_value()['children'].append({
                id: c,
                'children': [],
            })

    def get_display_text(self):
        obj = self.get_value()
        if isinstance(obj, dict):
            # it's the root
            return obj['title']
        return self.get_value().get_title()


class ExpandablePage(Page):
    """This class can 'expand', i.e. load a list of subpages"""

    def __init__(self, data):
        super().__init__(data)
        self.expanded = False

    def get_children(self):
        self.expanded = True
        log.debug("Load child pages of %s..." % self.id)
        url = f"rest/api/content/{self.id}/child/page"
        params = {
            'expand': 'body,version,history.lastUpdated,space',
        }
        r = make_request(url, params=params)
        result = r.json()['results']
        result = [ExpandablePage(p) for p in result]
        log.debug("Retrieved %d items" % len(result))
        return result


PluginView = SpaceView
