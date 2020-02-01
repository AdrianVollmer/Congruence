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


from congruence.logging import log
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
    ]

    def __init__(self, data, wrapper):
        self.wrapper = wrapper
        topnode = CongruenceParentNode(self.wrapper, data)
        super().__init__(urwid.TreeWalker(topnode))

    def key_action(self, action, size=None):
        log.debug('key_action %s' % action)
        if action == 'move down':
            urwid.TreeListBox.keypress(self, size, 'down')
        elif action == 'move up':
            urwid.TreeListBox.keypress(self, size, 'up')
        elif action == 'page down':
            urwid.TreeListBox.keypress(self, size, 'page down')
        elif action == 'page up':
            urwid.TreeListBox.keypress(self, size, 'page up')
        elif action == 'toggle collapse':
            node = self.get_focus()[0]
            node.expanded = not node.expanded
            node.update_expanded_icon()
        elif action == 'next view':
            view = self.get_focus()[0].get_next_view()
            if view:
                self.app.push_view(view)
        else:
            raise KeyError("Unknown key action: %s" % action)


class CongruenceTreeListBoxEntry(urwid.TreeWidget):
    """ Display widget for leaf nodes """

    def __init__(self, node):
        self.node = node
        super().__init__(node)

    def get_display_text(self):
        return "TODO"


class CongruenceCardTreeWidget(CongruenceTreeListBoxEntry):
    """This class can be used to display a carded TreeWidget"""

    indent_cols = 2

    def get_value(self):
        node = list(self.get_node().get_value().values())[0]
        return node

    def get_display_header(self):
        node = self.get_value()
        try:
            return node.get_title()
        except AttributeError:
            return "Root"

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

    def get_indented_widget(self):
        widget = self.get_inner_widget()
        indent_cols = self.get_indent_cols()
        return urwid.Padding(widget, width=('relative', 100), left=indent_cols)

    def update_expanded_icon(self):
        """Update display widget text for parent widgets"""
        # icon is first element in header widget
        self._w.base_widget.widget_list[0].base_widget.widget_list[0] = [
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
