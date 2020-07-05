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
    CongruenceTextBox, CollectKeyActions, key_action
import congruence.environment as env

import urwid

import re


class CongruenceListBox(CongruenceView, urwid.ListBox,
                        metaclass=CollectKeyActions):
    """Displays a list of CongruenceListBoxEntry objects

    :entries: a list of CongruenceListBoxEntry objects

    """

    def __init__(self, entries, help_string=None):
        self.entries = entries
        self.help_string = help_string
        self.walker = urwid.SimpleFocusListWalker(self.entries)
        self._search_eesults = []
        super().__init__(self.walker)
        if self.entries and isinstance(self.entries[0], ColumnListBoxEntry):
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

    @key_action
    def move_down(self, size=None):
        urwid.ListBox.keypress(self, size, 'down')

    @key_action
    def move_up(self, size=None):
        urwid.ListBox.keypress(self, size, 'up')

    @key_action
    def page_down(self, size=None):
        urwid.ListBox.keypress(self, size, 'page down')

    @key_action
    def page_up(self, size=None):
        urwid.ListBox.keypress(self, size, 'page up')

    @key_action
    def scroll_to_bottom(self, size=None):
        self.set_focus(0, coming_from='above')

    @key_action
    def scroll_to_top(self, size=None):
        self.set_focus(0, coming_from='below')

    @key_action
    def next_view(self, size=None):
        view = self.get_focus()[0].get_next_view()
        if view:
            env.app.push_view(view)

    @key_action
    def show_details(self, size=None):
        view = self.get_focus()[0].get_details_view()
        if view:
            env.app.push_view(view)

    @key_action
    def search(self, size=None):
        self._search()

    @key_action
    def search_next(self, size=None):
        self._search_next(1)

    @key_action
    def search_prev(self, size=None):
        self._search_next(-1)

    @key_action
    def limit(self, size=None):
        def limit_inner(expr):
            _search_results = [
                e for e in self.entries if e.search_match(expr)
            ]
            self.walker[:] = _search_results
            if expr == '.':
                env.app.reset_status()
            else:
                env.app.alert("To view all items, limit to '.'.", 'info')

        env.app.get_input(
            'Search for:',
            limit_inner,
        )

    def _search(self):
        def search_inner(expr):
            self._search_results = [
                e[0] for e in enumerate(self.entries)
                if e[1].search_match(expr)
            ]
            env.app.alert("Found %d results" % len(self._search_results),
                          'info')
            if self._search_results:
                self._current_search_result = 0
                pos = self._search_results[self._current_search_result]
                self.set_focus(pos)
        env.app.get_input(
            'Search for:',
            search_inner,
        )

    def _search_next(self, count=1):
        if self._search_results:
            self._current_search_result += count
            self._current_search_result %= len(self._search_results)
            pos = self._search_results[self._current_search_result]
            self.set_focus(pos)


class CongruenceListBoxEntry(urwid.WidgetWrap):
    """Represents one item in a ListBox

    :obj: a confluence content object or a string
    """

    def __init__(self, obj):
        self.obj = obj
        self._inner_widget = self.wrap_in_widget()

        self._widget = urwid.AttrMap(
            self._inner_widget,
            attr_map="body",
            focus_map="focus",
        )
        super().__init__(self._widget)

    def wrap_in_widget(self):
        try:
            return urwid.Text(self.obj.get_title())
        except AttributeError:
            return urwid.Text(self.obj)

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

        if isinstance(self.obj, str):
            return re.search(search_string, self.obj)
        return self.obj.match(search_string)


class CardedListBoxEntry(CongruenceListBoxEntry):
    """Represents one item in a ListBox with columns

    :obj: a confluence content object which implements get_head() and
        get_content()
    """
    def render_head(self):
        head = self.obj.get_head()
        return urwid.AttrMap(
            urwid.Text(head),
            'card-head',
            focus_map='card-focus'
        )

    def render_content(self):
        text = self.obj.get_content()
        return urwid.AttrMap(urwid.Text(text), 'body')

    def wrap_in_widget(self):
        return urwid.Pile([
            self.render_head(),
            self.render_content(),
        ])


class ColumnListBoxEntry(CongruenceListBoxEntry):
    """Represents one item in a ListBox with columns

    :obj: a confluence content object which implements get_columns()
    """
    def wrap_in_widget(self):
        self._columns = self.obj.get_columns()
        assert len(self._columns) == 5
        return urwid.Columns(
            [(urwid.Text(t, wrap='clip')) for t in self._columns],
            dividechars=1,
        )
