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


class ConfluenceTreeListBox(urwid.TreeListBox):
    pass


class ConfluenceTree:
    footer_text = [
        ('title', "Confluence Data Browser"), "    ",
        ('key', "UP"), ",",
        ('key', "DOWN"), ",",
        ('key', "PAGE UP"), ",",
        ('key', "PAGE DOWN"), "  ",
        ('key', "+"), ",",
        ('key', "-"), "  ",
        ('key', "LEFT"), "  ",
        ('key', "HOME"), "  ",
        ('key', "END"), "  ",
        ('key', "Q"),
        ]

    def __init__(self, data=None):
        self.topnode = ConfluenceParentNode(data)
        self.listbox = ConfluenceTreeListBox(urwid.TreeWalker(self.topnode))
        self.listbox.offset_rows = 1
        self.header = urwid.Text("")
        self.footer = urwid.AttrWrap(urwid.Text(self.footer_text), 'foot')
        self.view = urwid.Frame(
            urwid.AttrWrap(self.listbox, 'body'),
            header=urwid.AttrWrap(self.header, 'head'),
            footer=self.footer
        )

    def main(self):
        """Run the program."""

        self.loop = urwid.MainLoop(self.view,
                                   PALETTE,
                                   unhandled_input=self.unhandled_input)
        self.loop.run()

    def unhandled_input(self, k):
        if k in ('q', 'Q'):
            raise urwid.ExitMainLoop()
