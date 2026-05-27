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

from __future__ import annotations

from typing import Any, cast

import urwid

from congruence.views.common import CollectKeyActions, CongruenceTextBox, CongruenceView, key_action


class CongruenceListBox(CongruenceView, urwid.ListBox, metaclass=CollectKeyActions):
    """ListBox displaying a sequence of CongruenceListBoxEntry objects."""

    def __init__(self, entries: list, help_string: str | None = None) -> None:
        self.entries = entries
        self.help_string = help_string
        self.walker = urwid.SimpleFocusListWalker(self.entries)
        self._search_results: list[int] = []
        self._current_search_result: int = 0
        super().__init__(self.walker)
        if self.entries and isinstance(self.entries[0], ColumnListBoxEntry):
            self.align_columns()

    def align_columns(self) -> None:
        """Set every column to its maximum width across all entries."""
        widths: list[int] | None = None
        for e in self.entries:
            if hasattr(e, "_columns") and e._columns:
                this_widths = list(map(len, e._columns))
                if widths:
                    for i, w in enumerate(this_widths):
                        widths[i] = max(widths[i], w)
                else:
                    widths = this_widths
        if widths:
            for e in self.entries:
                for i, w in enumerate(widths[:-1]):
                    item = e._inner_widget.contents[i]
                    e._inner_widget.contents[i] = (
                        item[0],
                        e._inner_widget.options("given", w, False),
                    )

    def redraw(self) -> None:
        self.walker[:] = self.entries
        self.align_columns()

    @key_action
    def move_down(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "down")

    @key_action
    def move_up(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "up")

    @key_action
    def page_down(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "page down")

    @key_action
    def page_up(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "page up")

    @key_action
    def scroll_to_bottom(self, size: tuple | None = None) -> None:
        self.set_focus(0, coming_from="above")

    @key_action
    def scroll_to_top(self, size: tuple | None = None) -> None:
        self.set_focus(0, coming_from="below")

    @key_action
    def next_view(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        if node is None:
            return
        view = node.get_next_view()
        if view is not None:
            self.app.push_view(view)

    @key_action
    def show_details(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        if node is None:
            return
        view = node.get_details_view()
        if view is not None:
            self.app.push_view(view)

    @key_action
    def search(self, size: tuple | None = None) -> None:
        self._search()

    @key_action
    def search_next(self, size: tuple | None = None) -> None:
        self._search_next(1)

    @key_action
    def search_prev(self, size: tuple | None = None) -> None:
        self._search_next(-1)

    @key_action
    def limit(self, size: tuple | None = None) -> None:
        def limit_inner(expr: str) -> None:
            filtered = [e for e in self.entries if e.search_match(expr)]
            self.walker[:] = filtered
            if expr == ".":
                self.app.reset_status()
            else:
                self.app.alert("To view all items, limit to '.'.", "info")

        self.app.get_input("Search for:", limit_inner)

    def _search(self) -> None:
        def search_inner(expr: str) -> None:
            self._search_results = [i for i, e in enumerate(self.entries) if e.search_match(expr)]
            self.app.alert(f"Found {len(self._search_results)} results", "info")
            if self._search_results:
                self._current_search_result = 0
                self.set_focus(self._search_results[0])

        self.app.get_input("Search for:", search_inner)

    def _search_next(self, count: int = 1) -> None:
        if self._search_results:
            self._current_search_result = (self._current_search_result + count) % len(self._search_results)
            self.set_focus(self._search_results[self._current_search_result])


class CongruenceListBoxEntry(urwid.WidgetWrap):
    """Represents one row in a CongruenceListBox."""

    def __init__(self, obj: Any) -> None:
        self.obj = obj
        self._inner_widget = self.wrap_in_widget()
        self._widget = urwid.AttrMap(self._inner_widget, attr_map="body", focus_map="focus")
        super().__init__(self._widget)

    def wrap_in_widget(self) -> urwid.Widget:
        try:
            return urwid.Text(self.obj.get_title())
        except AttributeError:
            return urwid.Text(self.obj)

    def selectable(self) -> bool:
        return True

    def keypress(self, size: tuple, key: str) -> str:
        return key

    def get_next_view(self) -> object | None:
        return None

    def get_details_view(self) -> CongruenceTextBox:
        text = self.obj.get_json()
        view = CongruenceTextBox(text)
        view.title = "Details"
        return view

    def search_match(self, search_string: str) -> bool:
        raise NotImplementedError(f"search_match in {type(self).__name__}")


class CardedListBoxEntry(CongruenceListBoxEntry):
    """List entry rendered with a header row and a content row."""

    def render_head(self) -> urwid.AttrMap:
        return urwid.AttrMap(urwid.Text(self.obj.get_head()), "card-head", focus_map="card-focus")

    def render_content(self) -> urwid.AttrMap:
        return urwid.AttrMap(urwid.Text(self.obj.get_content()), "body")

    def wrap_in_widget(self) -> urwid.Pile:
        return urwid.Pile([self.render_head(), self.render_content()])


class ColumnListBoxEntry(CongruenceListBoxEntry):
    """List entry rendered as five fixed-width columns."""

    def wrap_in_widget(self) -> urwid.Columns:
        self._columns: list[str] = self.obj.get_columns()
        assert len(self._columns) == 5
        return urwid.Columns([(urwid.Text(t, wrap="clip")) for t in self._columns], dividechars=1)
