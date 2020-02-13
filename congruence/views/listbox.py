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


#  from congruence.logging import log
from congruence.views.common import CongruenceView, \
    RememberParentKeyMapMeta, CongruenceTextBox

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

    def ka_move_down(self, size=None):
        urwid.ListBox.keypress(self, size, 'down')

    def ka_move_up(self, size=None):
        urwid.ListBox.keypress(self, size, 'up')

    def ka_page_down(self, size=None):
        urwid.ListBox.keypress(self, size, 'page down')

    def ka_page_up(self, size=None):
        urwid.ListBox.keypress(self, size, 'page up')

    def ka_scroll_to_bottom(self, size=None):
        self.set_focus(0, coming_from='above')

    def ka_scroll_to_top(self, size=None):
        self.set_focus(0, coming_from='below')

    def ka_next_view(self, size=None):
        view = self.get_focus()[0].get_next_view()
        if view:
            self.app.push_view(view)

    def ka_show_details(self, size=None):
        view = self.get_focus()[0].get_details_view()
        if view:
            self.app.push_view(view)

    def ka_search(self, size=None):
        self.search()

    def ka_search_next(self, size=None):
        self.search_next(1)

    def ka_search_prev(self, size=None):
        self.search_next(-1)

    def ka_limit(self, size=None):
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
    :structure: can be one of 'flat', 'columns' and 'carded' and determines
        the structure of the ListBox entry.
    """

    def __init__(self, obj, structure='flat'):
        self.obj = obj
        self.structure = structure
        if self.structure == 'flat':
            self.cols = False
            if hasattr(obj, 'get_title'):
                self._inner_widget = urwid.Text(obj.get_title())
            else:
                self._inner_widget = urwid.Text(str(obj))
        elif self.structure == 'columns':
            self._columns = obj.get_title(cols=True)
            self._inner_widget = urwid.Columns(
                [(urwid.Text(t, wrap='clip')) for t in self._columns],
                dividechars=1,
            )
        elif self.structure == 'carded':
            self._widget = urwid.Pile([
                self.render_head(),
                self.render_content(),
            ])
        else:
            raise KeyError("Invalid structure: %s" % structure)
        if not structure == 'carded':
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
        text = self.obj.get_json()
        view = CongruenceTextBox(text)
        view.title = "Details"
        return view

    def search_match(self, search_string):
        """Returns a Boolean whether the search string matches"""

        raise NotImplementedError("search_match in %s" % type(self).__name__)

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
