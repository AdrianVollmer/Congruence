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


class CongruenceTreeListBox(urwid.TreeListBox, CongruenceView,
                            metaclass=RememberParentKeyMapMeta):
    """Displays a tree view of 'wrapper' objects

    :data: a tree-like dict-structure. Each dictionary needs to have the keys
        'name' and 'children'. The latter is a list of dictionaries and the
        former is an arbitrary dictionary which is passed to the constructor
        of wrapper.
    :wrapper: some subclass of CongruenceTreeWidget.
    """

    key_map = {
        'k': ('move up', 'move up'),
        'j': ('move down', 'move down'),
        '[': ('page up', 'move page up'),
        ']': ('page down', 'move page down'),
    }

    def __init__(self, data, wrapper):
        self.wrapper = wrapper
        topnode = CongruenceParentNode(self.wrapper, data)
        super().__init__(urwid.TreeWalker(topnode))


class CongruenceTreeListBoxEntry(urwid.TreeWidget):
    """ Display widget for leaf nodes """

    def __init__(self, node, key_map={}):
        self.node = node
        self.key_map = key_map
        super().__init__(node)

    def get_display_text(self):
        return "TODO"

    def keypress(self, size, key):
        log.debug("Keypress in TreeListBoxEntry: %s" % key)
        for k, v in self.key_map.items():
            if k == key:
                data = list(self.node.get_value().values())[0]
                self.app.push_view(v(data))
                return
        return key


class CongruenceCardTreeWidget(CongruenceTreeListBoxEntry):
    """This class can be used to display a carded TreeWidget"""

    indent_cols = 2

    def get_value(self):
        node = list(self.get_node().get_value().values())[0]
        return node

    def get_display_header(self):
        node = self.get_value()
        if node["title"] == 'root':
            return "Root"
        else:
            return node["title"]

    def get_display_body(self):
        node = self.get_value()
        if node["title"] == 'root':
            return ""
        else:
            return node["content"]

    def load_inner_widget(self):
        """Build a multi-line widget with a header and a body"""

        icon = [self.unexpanded_icon, self.expanded_icon][self.expanded]
        header = urwid.Text(self.get_display_header())
        header = urwid.Columns([('fixed', 1, icon), header], dividechars=1)
        header = urwid.AttrWrap(header, 'head')
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
