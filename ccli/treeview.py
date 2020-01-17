from ccli.palette import PALETTE
import urwid


# Inspired by the example in the urwid library. Copyright notice:
# Trivial data browser
#    This version:
#      Copyright (C) 2010  Rob Lanphier
#    Derived from browse.py in urwid distribution
#      Copyright (C) 2004-2007  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/


class ConfluenceTreeWidget(urwid.TreeWidget):
    """ Display widget for leaf nodes """
    def get_display_text(self):
        if 'name' in self.get_node().get_value():
            return self.get_node().get_value()['name']
        else:
            return self.get_node().get_value()['title']


class ConfluenceNode(urwid.TreeNode):
    """ Data storage object for leaf nodes """
    def load_widget(self):
        return ConfluenceTreeWidget(self)


class ConfluenceParentNode(urwid.ParentNode):
    """ Data storage object for interior/parent nodes """
    def load_widget(self):
        return ConfluenceTreeWidget(self)

    def load_child_keys(self):
        data = self.get_value()
        return range(len(data['children']))

    def load_child_node(self, key):
        """Return either an ConfluenceNode or ConfluenceParentNode"""
        childdata = self.get_value()['children'][key]
        childdepth = self.get_depth() + 1
        if 'children' in childdata:
            childclass = ConfluenceParentNode
        else:
            childclass = ConfluenceNode
        return childclass(childdata, parent=self, key=key, depth=childdepth)

    def __iter__(self):
        yield from self.data

    def __getitem__(self, item):
        return self.data[item]


class ConfluenceTreeListBox(urwid.TreeListBox):
    def __init__(self, topnode, app):
        super().__init__(topnode)
        self.app = app

    def keypress(self, size, key):
        # TODO allow custom key bindings
        if key == 'k':
            key = 'up'
            super().keypress(size, key)
            return
        if key == 'j':
            key = 'down'
            super().keypress(size, key)
            return
        if key == 'enter':
            selected_item = self.app.listbox.get_focus()[1].get_value()
            #  self.app.loop.widget = selected_item.view()
            self.app.push_view(selected_item.view(self.app))
        if key == "?":
            pass
        self.app.unhandled_input(key)


class ConfluenceApp(object):
    footer_text = [
        ('title', "Confluence CLI"), "    press ? for help",
    ]

    def unhandled_input(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    def __init__(self, data=None):
        self.topnode = ConfluenceParentNode(data)
        self.listbox = ConfluenceTreeListBox(urwid.TreeWalker(self.topnode),
                                             self)
        self.listbox.offset_rows = 1
        self.footer = urwid.AttrWrap(urwid.Text(self.footer_text), 'foot')
        self.view = urwid.Frame(
            urwid.AttrWrap(self.listbox, 'body'),
            footer=self.footer
        )
        self._view_stack = []

    def push_view(self, view):
        self._view_stack.append(self.loop.widget)
        self.loop.widget = view

    def pop_view(self):
        try:
            view = self._view_stack.pop()
            self.loop.widget = view
        except IndexError:
            self.loop.widget = self.view

    def main(self):
        """Run the program."""

        self.loop = urwid.MainLoop(
            self.view,
            PALETTE,
            unhandled_input=self.unhandled_input)
        self.loop.run()
