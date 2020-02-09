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
from congruence.views.common import CongruenceView, RememberParentKeyMapMeta

import urwid


class CongruenceTreeListBox(CongruenceView, urwid.TreeListBox,
                            metaclass=RememberParentKeyMapMeta):
    """Displays a tree view of 'wrapper' objects

    :data: a tree-like dict-structure. Each dictionary needs to have the keys
        'name' and 'children'. The latter is a list of dictionaries and the
        former is an arbitrary dictionary which is passed to the constructor
        of wrapper.
    :wrapper: some subclass of CongruenceTreeWidget.
    """

    key_actions = [
        'move up',
        'move down',
        'page up',
        'page down',
        'show details',
        'next view',
        'search',
        'search next',
        'search prev',
    ]

    def __init__(self, data, wrapper, help_string=None):
        self.wrapper = wrapper
        self.help_string = help_string
        self.topnode = CongruenceParentNode(self.wrapper, data)
        self.walker = urwid.TreeWalker(self.topnode)
        super().__init__(self.walker)

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

    def ka_toggle_collapse(self, size=None):
        node = self.get_focus()[0]
        node.expanded = not node.expanded
        node.update_expanded_icon()

    def ka_next_view(self, size=None):
        view = self.get_focus()[0].get_next_view()
        if view:
            self.app.push_view(view)

    def ka_search(self, size=None):
        self.search()

    def ka_search_next(self, size=None):
        self.search_next(1)

    def ka_search_prev(self, size=None):
        self.search_next(-1)

    def search(self):
        def search(expr):
            self._search_results = []
            node = self.topnode
            while True:
                node = self.walker.get_next(node)[1]
                if not node:
                    break
                if node.search_match(expr):
                    self._search_results.append(node)

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


class CongruenceTreeListBoxEntry(urwid.TreeWidget):
    """Display widget for nodes"""

    indent_cols = 2

    def __init__(self, node):
        self.node = node
        super().__init__(node)

    def get_display_text(self):
        return list(self.node.get_value().keys())[0]

    def get_value(self):
        node = list(self.get_node().get_value().values())[0]
        return node

    def get_indented_widget(self):
        widget = self.get_inner_widget()
        indent_cols = self.get_indent_cols()
        return urwid.Padding(widget, width=('relative', 100), left=indent_cols)

    def update_expanded_icon(self):
        """Update display widget text for parent widgets"""
        self._w.base_widget.widget_list[0] = [
            self.unexpanded_icon, self.expanded_icon][self.expanded]

    def load_inner_widget(self):
        """Build a row widget with a text content"""

        self.icon = [self.unexpanded_icon, self.expanded_icon][self.expanded]
        header = urwid.Text(self.get_display_text())
        header = urwid.Columns([('fixed', 1, self.icon), header],
                               dividechars=1)
        header = urwid.AttrWrap(header, 'body', 'focus')
        widget = header
        return widget

    def selectable(self):
        return True


class CongruenceCardTreeWidget(CongruenceTreeListBoxEntry):
    """This class can be used to display a carded TreeWidget"""

    def get_display_header(self):
        node = self.get_value()
        try:
            return node.get_title()
        except AttributeError:
            return node['title']

    def get_display_body(self):
        node = self.get_value()
        try:
            return node.get_content()
        except AttributeError:
            return ""

    def load_inner_widget(self):
        """Build a multi-line widget with a header and a body"""

        self.icon = [self.unexpanded_icon, self.expanded_icon][self.expanded]
        header = urwid.Text(self.get_display_header())
        header = urwid.Columns([('fixed', 1, self.icon), header],
                               dividechars=1)
        header = urwid.AttrWrap(header, 'card-head', 'card-focus')
        if self.get_display_body():
            body = urwid.AttrWrap(urwid.Text(self.get_display_body()), 'body')
            widget = urwid.Pile([header, body])
        else:
            widget = header
        return widget

    def update_expanded_icon(self):
        """Update display widget text for parent widgets"""
        # icon is first element in header widget
        try:
            self._w.base_widget.widget_list[0].base_widget.widget_list[0] = [
                self.unexpanded_icon, self.expanded_icon][self.expanded]
        except AttributeError:
            # it's the root
            self._w.base_widget.widget_list[0] = [
                self.unexpanded_icon, self.expanded_icon][self.expanded]


class CongruenceNode(urwid.TreeNode):
    """ Data storage object for leaf nodes """

    def __init__(self, wrapper, data, **kwargs):
        self.wrapper = wrapper
        super().__init__(data, **kwargs)

    def load_widget(self):
        return self.wrapper(self)


class CongruenceParentNode(urwid.ParentNode):
    """ Data storage object for interior/parent nodes """

    def __init__(self, wrapper, data, **kwargs):
        self.wrapper = wrapper
        super().__init__(data, **kwargs)

    def load_widget(self):
        return self.wrapper(self)

    def load_child_keys(self):
        data = self.get_value()
        return range(len(data['children']))

    def load_child_node(self, key):
        """Return either an CongruenceNode or CongruenceParentNode"""
        childdata = self.get_value()['children'][key]
        childdepth = self.get_depth() + 1
        if 'children' in childdata:
            childclass = CongruenceParentNode
        else:
            childclass = CongruenceNode
        return childclass(self.wrapper,
                          childdata, parent=self, key=key, depth=childdepth)

    def search_match(self, expr):
        obj = self.get_widget().get_value()
        return obj.match(expr)
