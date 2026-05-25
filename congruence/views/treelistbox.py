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


class CongruenceTreeListBox(CongruenceView, urwid.TreeListBox, metaclass=CollectKeyActions):
    """Tree view for hierarchical Confluence content.

    :data: nested dict structure; each node needs 'children' key.
    :wrapper: subclass of CongruenceTreeListBoxEntry used to render each node.
    """

    def __init__(self, data: dict, wrapper: type, help_string: str | None = None) -> None:
        self.wrapper = wrapper
        self.help_string = help_string
        self._search_results: list = []
        self._current_search_result: int = 0
        self.topnode = CongruenceParentNode(self.wrapper, data)
        self.walker = urwid.TreeWalker(self.topnode)
        super().__init__(self.walker)

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
    def toggle_collapse(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        if node is None:
            return
        node.expanded = not node.expanded  # type: ignore[union-attr]
        node.update_expanded_icon()  # type: ignore[union-attr]

    @key_action
    def next_view(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        if node is None:
            return
        view = node.get_next_view()  # type: ignore[union-attr]
        if view:
            self.app.push_view(view)

    @key_action
    def show_details(self, size: tuple | None = None) -> None:
        node = self.get_focus()[0]
        if node is None:
            return
        view = node.get_details_view()  # type: ignore[union-attr]
        if view:
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

    def _search(self) -> None:
        def search_inner(expr: str) -> None:
            self._search_results = []
            node = self.topnode
            while True:
                node = self.walker.get_next(node)[1]
                if not node:
                    break
                if node.search_match(expr):  # type: ignore[union-attr]
                    self._search_results.append(node)
            self.app.alert(f"Found {len(self._search_results)} results", "info")
            if self._search_results:
                self._current_search_result = 0
                self.set_focus(self._search_results[0])

        self.app.get_input("Search for:", search_inner)

    def _search_next(self, count: int = 1) -> None:
        if self._search_results:
            self._current_search_result = (self._current_search_result + count) % len(self._search_results)
            self.set_focus(self._search_results[self._current_search_result])


class CongruenceTreeListBoxEntry(urwid.TreeWidget):
    """Display widget for tree nodes."""

    indent_cols: int = 2

    def __init__(self, node: Any) -> None:
        self.node = node
        super().__init__(node)

    def get_display_text(self) -> str:
        return next(iter(self.node.get_value().keys()))

    def get_value(self) -> Any:
        return next(iter(self.get_node().get_value().values()))

    def get_indented_widget(self) -> urwid.Padding:
        widget = self.get_inner_widget()
        indent_cols = self.get_indent_cols()
        return urwid.Padding(widget, width=("relative", 100), left=indent_cols)

    def update_expanded_icon(self) -> None:
        self._w.base_widget.widget_list[0] = [self.unexpanded_icon, self.expanded_icon][self.expanded]  # type: ignore[union-attr,index]

    def load_inner_widget(self) -> urwid.Widget:
        self.icon = [self.unexpanded_icon, self.expanded_icon][self.expanded]
        header = urwid.Text(self.get_display_text())
        header = urwid.Columns([("fixed", 1, self.icon), header], dividechars=1)  # type: ignore[arg-type]
        return urwid.AttrWrap(header, "body", "focus")

    def selectable(self) -> bool:
        return True

    def get_details_view(self) -> CongruenceTextBox | None:
        if isinstance(self.get_value(), dict):
            return None
        text = self.get_value().get_json()
        view = CongruenceTextBox(text)
        view.title = "Details"
        return view


class CongruenceCardTreeWidget(CongruenceTreeListBoxEntry):
    """Tree widget with a card-style (header + body) layout."""

    def get_display_header(self) -> str:
        node = self.get_value()
        try:
            return node.get_head()
        except AttributeError:
            return node["title"]

    def get_display_body(self) -> str:
        node = self.get_value()
        try:
            return node.get_content()
        except AttributeError:
            return ""

    def load_inner_widget(self) -> urwid.Widget:
        self.icon = [self.unexpanded_icon, self.expanded_icon][self.expanded]
        header = urwid.Text(self.get_display_header())
        header = urwid.Columns([("fixed", 1, self.icon), header], dividechars=1)  # type: ignore[arg-type]
        header = urwid.AttrWrap(header, "card-head", "card-focus")
        if self.get_display_body():
            body = urwid.AttrWrap(urwid.Text(self.get_display_body()), "body")
            return urwid.Pile([header, body])
        return header

    def update_expanded_icon(self) -> None:
        try:
            self._w.base_widget.widget_list[0].base_widget.widget_list[0] = [  # type: ignore[union-attr,index]
                self.unexpanded_icon,
                self.expanded_icon,
            ][self.expanded]
        except AttributeError:
            self._w.base_widget.widget_list[0] = [self.unexpanded_icon, self.expanded_icon][self.expanded]  # type: ignore[union-attr,index]


class CongruenceNode(urwid.TreeNode):
    """Leaf node data storage."""

    def __init__(self, wrapper: type, data: Any, **kwargs: Any) -> None:
        self.wrapper = wrapper
        super().__init__(data, **kwargs)

    def load_widget(self) -> CongruenceTreeListBoxEntry:
        return self.wrapper(self)


class CongruenceParentNode(urwid.ParentNode):
    """Interior/parent node data storage."""

    def __init__(self, wrapper: type, data: Any, **kwargs: Any) -> None:
        self.wrapper = wrapper
        super().__init__(data, **kwargs)

    def load_widget(self) -> CongruenceTreeListBoxEntry:
        return self.wrapper(self)

    def load_child_keys(self) -> range:
        return range(len(self.get_value()["children"]))

    def load_child_node(self, key: int) -> CongruenceNode | CongruenceParentNode:
        childdata = self.get_value()["children"][key]
        childdepth = self.get_depth() + 1
        childclass = CongruenceParentNode if "children" in childdata else CongruenceNode
        return childclass(self.wrapper, childdata, parent=self, key=key, depth=childdepth)

    def search_match(self, expr: str) -> bool:
        obj = self.get_widget().get_value()  # type: ignore[union-attr]
        return obj.match(expr)  # type: ignore[union-attr]
