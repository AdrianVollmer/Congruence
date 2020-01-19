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

# Inspired by the example in the urwid library. Copyright notice:
# Trivial data browser
#    This version:
#      Copyright (C) 2010  Rob Lanphier
#    Derived from browse.py in urwid distribution
#      Copyright (C) 2004-2007  Ian Ward
# Urwid web site: http://excess.org/urwid/

from congruence.args import config
from congruence.palette import PALETTE
from congruence.logging import log

from importlib import import_module

import urwid


class ConfluenceTreeWidget(urwid.TreeWidget):
    """ Display widget for leaf nodes """

    def get_display_text(self):
        if 'name' in self.get_node().get_value():
            return self.get_node().get_value()['name']
        else:
            return self.get_node().get_value()['title']


class ConfluenceNode(urwid.TreeNode):
    """ Data storage object for leaf nodes """

    def __init__(self, WidgetClass, data, **kwargs):
        self.WidgetClass = WidgetClass
        super().__init__(data, **kwargs)

    def load_widget(self):
        return self.WidgetClass(self)


class ConfluenceParentNode(urwid.ParentNode):
    """ Data storage object for interior/parent nodes """

    def __init__(self, WidgetClass, data, **kwargs):
        self.WidgetClass = WidgetClass
        super().__init__(data, **kwargs)

    def load_widget(self):
        return self.WidgetClass(self)

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
        return childclass(self.WidgetClass,
                          childdata, parent=self, key=key, depth=childdepth)


class ConfluenceTreeListBox(urwid.TreeListBox):
    """Displays a tree view of 'WidgetClass' objects

    data: a tree-like dict-structure. Each dictionary needs to have the keys
        'name' and 'children'. The latter is a list of dictionaries and the
        former is an arbitrary dictionary which is passed to the constructor
        of WidgetClass.
    WidgetClass: some subclass of ConfluenceTreeWidget whose constructor
        takes a dictionary.

    """

    def __init__(self, data, WidgetClass):
        self.WidgetClass = WidgetClass
        topnode = ConfluenceParentNode(self.WidgetClass, data)
        super().__init__(urwid.TreeWalker(topnode))

    def keypress(self, size, key):
        if key == 'k':
            key = 'up'
            super().keypress(size, key)
            return
        if key == 'j':
            key = 'down'
            super().keypress(size, key)
            return
        #  if key == 'enter':
        #      selected_item = self.app.listbox.get_focus()[1].get_value()
        #      self.app.push_view(selected_item.view().build())
        #      return
        #  if key == "?":
        #      pass
        return key
        #  self.app.unhandled_input(key)


class ConfluenceSimpleListEntry(urwid.WidgetWrap):
    def __init__(self, text, view=None):
        self.text = text
        self.view = view
        widget = urwid.AttrMap(
            urwid.Text(self.text),
            attr_map="body",
            focus_map="focus",
        )
        super().__init__(widget)

    def selectable(self):
        return True

    def keypress(self, size, key):
        log.debug("Keypress in ListEntry %s: %s" % (self.text, key))
        return key


class ConfluenceListBox(urwid.ListBox):
    """Displays a list of ConfluenceSimpleListEntry objects"""

    def __init__(self, entries):
        self.entries = entries
        super().__init__(urwid.SimpleFocusListWalker(self.entries))

    def keypress(self, size, key):
        log.debug("Keypress in %s: %s" % ("ConfluenceListBox", key))
        if key == 'j':
            key = 'down'
            super().keypress(size, key)
            return
        if key == 'k':
            key = 'up'
            super().keypress(size, key)
            return
        return key


class ConfluenceMainView(urwid.Frame):
    """Represents the main view of the app

    body_builder: A function, which takes no arguments and returns a
        urwid.Widget which implemented get_focus(). This widget can have a
        'view' attribute of type ConfluenceMainView, which will be shown
        when 'enter' is pressed.
    title_text: an optional text for the header
    footer_text: an optional text for the footer

    Every plugin should subclass this view.
    """

    def __init__(self, body_builder, title_text="", footer_text=""):
        self.body_builder = body_builder
        self.title_text = title_text
        self.footer_text = footer_text
        self.footer = urwid.AttrWrap(urwid.Text(self.footer_text), 'foot')
        self.header = urwid.AttrWrap(urwid.Text(self.title_text), 'head')

    def build(self):
        view = self.body_builder()
        if view:
            super().__init__(
                view,
                footer=self.footer,
                header=self.header,
            )
            return self
        return None

    def keypress(self, size, key):
        log.debug("Keypress in %s: %s" % (self.title_text, key))
        if key == 'enter':
            node = self.body.get_focus()[0]
            if hasattr(node, "view") and node.view:
                log.debug("Push View")
                next_view = node.view.build()
                if next_view:
                    self.app.push_view(next_view)
                    return None
                # Redraw screen, because we're probably coming back from
                # another app (cli browser or editor)
                self.app.loop.screen.clear()
        if key == 'q':
            self.app.pop_view()
            return None
        return self.body.keypress(size, key)


class ConfluenceApp(object):
    """This class represents the app"""

    def unhandled_input(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    def __init__(self):
        # Set this class variable so each instance can refer to the app
        # object
        ConfluenceMainView.app = self

        # Initialize view stack
        self._view_stack = []

        # Create a view of all plugins defined in the config
        self.entries = []
        for name, p in config["Plugins"].items():
            view = self.get_plugin_view(name, p)
            if p and "DisplayName" in p:
                name = p["DisplayName"]
            self.entries.append(
                ConfluenceSimpleListEntry(name, view=view),
            )
        self.view = ConfluenceMainView(
            lambda: ConfluenceListBox(self.entries),
            "congruence main menu",
            "foo",
        ).build()

    def push_view(self, view):
        """Open a new view and keep track of the old one"""
        self._view_stack.append(self.loop.widget)
        self.loop.widget = view

    def pop_view(self):
        """Restore the last view down the list"""
        if self._view_stack:
            view = self._view_stack.pop()
            self.loop.widget = view
        else:
            self.loop.widget = self.view

    def main(self):
        """Run the program."""

        self.loop = urwid.MainLoop(
            self.view,
            PALETTE,
            unhandled_input=self.unhandled_input)
        self.loop.run()

    def get_plugin_view(self, name, props={}):
        """This function builds the first view of the app"""
        view = getattr(
            import_module('congruence.confluence.' + name.lower()),
            "PluginView"
        )
        return view(props=props)
