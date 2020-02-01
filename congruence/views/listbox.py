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


#  from congruence.args import config
#  from congruence.palette import PALETTE
from congruence.logging import log
from congruence.views.common import CongruenceView, RememberParentKeyMapMeta

import urwid


class CongruenceListBox(CongruenceView, urwid.ListBox,
                        metaclass=RememberParentKeyMapMeta):
    """Displays a list of CongruenceListBoxEntry objects

    :entries: a list of CongruenceListBoxEntry objects

    """

    key_actions = [
        'move up',
        'move down',
        'page up',
        'page down',
        'search',
        'search next',
        'search prev',
        'limit',
        'show details',
        'next view',
        'scroll to bottom',
        'scroll to top',
    ]

    def __init__(self, entries, help_string=None):
        self.entries = entries
        self.help_string = help_string
        self.walker = urwid.SimpleFocusListWalker(self.entries)
        self._search_results = []
        super().__init__(self.walker)
        self.align_columns()

    def align_columns(self):
        """Set all column widths to its common maximum"""

        widths = None
        for e in self.entries:
            if hasattr(e, '_columns') and e._columns:
                this_widths = list(map(len, e._columns))
                if widths:
                    for i, w in enumerate(this_widths):
                        widths[i] = max(widths[i], w)
                else:
                    widths = this_widths
        if widths:
            for e in self.entries:
                for i, w in enumerate(widths[:-1]):
                    # [:-1] because the last column can be any width
                    item = e._inner_widget.contents[i]
                    _, _, box_widget = item[1]
                    e._inner_widget.contents[i] = (
                        item[0],
                        e._inner_widget.options('given', w, False),
                    )

    def redraw(self):
        self.walker[:] = self.entries
        self.align_columns()

    def key_action(self, action, size=None):
        log.debug('Process key action "%s"' % action)
        if action == 'move down':
            urwid.ListBox.keypress(self, size, 'down')
        elif action == 'move up':
            urwid.ListBox.keypress(self, size, 'up')
        elif action == 'page down':
            urwid.ListBox.keypress(self, size, 'page down')
        elif action == 'page up':
            urwid.ListBox.keypress(self, size, 'page up')
        elif action == 'scroll to bottom':
            self.set_focus(len(self.entries)-1)
        elif action == 'scroll to top':
            self.set_focus(0)
        elif action == 'next view':
            view = self.get_focus()[0].get_next_view()
            if view:
                self.app.push_view(view)
        elif action == 'show details':
            view = self.get_focus()[0].get_details_view()
            if view:
                view.title = "Details"
                self.app.push_view(view)
            else:
                self.app.alert("Looks like this item has no details",
                               "warning")
        elif action == 'search':
            self.search()
        elif action == 'search next':
            self.search_next(1)
        elif action == 'search prev':
            self.search_next(-1)
        elif action == 'limit':
            def limit(expr):
                _search_results = [
                    e for e in self.entries if e.search_match(expr)
                ]
                self.walker[:] = _search_results
                if expr == '.':
                    self.app.reset_status()
                else:
                    self.app.alert("To view all items, limit to '.'.", 'info')

            self.app.get_input(
                'Search for:',
                limit,
            )
        else:
            raise KeyError("Unknown key action: %s" % action)

    def search(self):
        def search(expr):
            self._search_results = [
                e[0] for e in enumerate(self.entries)
                if e[1].search_match(expr)
            ]
            self.app.alert("Found %d results" %
                           len(self._search_results),
                           'info')
            if self._search_results:
                self._current_search_result = 0
                pos = self._search_results[self._current_search_result]
                self.set_focus(pos)
        self.app.get_input(
            'Search for:',
            search,
        )

    def search_next(self, count=1):
        if self._search_results:
            self._current_search_result += count
            self._current_search_result %= len(self._search_results)
            pos = self._search_results[self._current_search_result]
            self.set_focus(pos)


class CongruenceListBoxEntry(urwid.WidgetWrap):
    """Represents one item in a ListBox

    :obj: a confluence content object or a string
    """

    def __init__(self, obj, cols=False):
        self.obj = obj
        self.cols = cols
        if isinstance(obj, str):
            self.cols = False
            self._inner_widget = urwid.Text(obj)
        elif cols:
            self._columns = obj.get_title(cols=cols)
            self._inner_widget = urwid.Columns(
                [('pack', urwid.Text(t)) for t in self._columns],
                dividechars=1,
            )
        else:
            self._inner_widget = urwid.Text(obj.get_title())
        self._widget = urwid.AttrMap(
            self._inner_widget,
            attr_map="body",
            focus_map="focus",
        )
        super().__init__(self._widget)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

    def get_next_view(self):
        return None

    def get_details_view(self):
        return None

    def search_match(self, search_string):
        """Returns a Boolean whether the search string matches"""

        raise NotImplementedError("search_match in %s" % type(self).__name__)


class CardListBoxEntry(urwid.Pile):
    def __init__(self, obj):
        self.obj = obj
        widgets = [
            self.render_head(),
            self.render_content(),
        ]
        super().__init__(widgets)

    def render_head(self):
        title = self.obj.get_title()
        return urwid.AttrMap(
            urwid.Text(title),
            'card-head',
            focus_map='card-focus'
        )

    def render_content(self):
        text = self.obj.get_content()
        return urwid.AttrMap(urwid.Text(text), 'body')

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key
