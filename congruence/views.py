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

"""
This file contains general 'views' (i.e. urwid widgets) which are
particular to this app and not to Confluence
"""

__help__ = """About Congruence:
    Adrian Vollmer, 2020

Main menu
"""

from congruence.args import config
from congruence.palette import PALETTE
from congruence.logging import log

from importlib import import_module

import urwid


class CongruenceTextBox(urwid.Widget):
    pass


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


class CongruenceTreeListBox(urwid.TreeListBox):
    """Displays a tree view of 'wrapper' objects

    :data: a tree-like dict-structure. Each dictionary needs to have the keys
        'name' and 'children'. The latter is a list of dictionaries and the
        former is an arbitrary dictionary which is passed to the constructor
        of wrapper.
    :wrapper: some subclass of CongruenceTreeWidget.
    """

    def __init__(self, data, wrapper):
        self.wrapper = wrapper
        topnode = CongruenceParentNode(self.wrapper, data)
        super().__init__(urwid.TreeWalker(topnode))

    def keypress(self, size, key):
        log.debug("Keypress in TreeListBox: %s", key)
        if key == 'k':
            key = 'up'
            self.keypress(size, key)
            return
        if key == 'j':
            key = 'down'
            self.keypress(size, key)
            return
        return super().keypress(size, key)
        #  return key


class CongruenceListBoxEntry(urwid.WidgetWrap):
    """Represents one item in a ListBox

    :data: an object holding data which this ListBoxEntry represents.
    :wrapper: a subclass of urwid.Widget whose constructor takes `data` as
        an argument.
    :key_map: a dictionary where the keys are literal keys and the values
        are functions or classes, which will be called with `data` as the
        argument when the corresponding key is pressed. The return values is
        pushed onto the view stack.
    """

    def __init__(self, data, wrapper, key_map={}):
        self.data = data
        self.key_map = key_map
        if isinstance(wrapper, str):
            widget = urwid.Text(wrapper)
        else:
            widget = wrapper(data)
        #  else:
        #      line = urwid.Columns(
        #          [('pack', urwid.Text(t)) for t in text],
        #          dividechars=1
        #      )
        widget = urwid.AttrMap(
            widget,
            attr_map="body",
            focus_map="focus",
        )
        super().__init__(widget)

    def selectable(self):
        return True

    def keypress(self, size, key):
        log.debug("Keypress in ListBoxEntry: %s" % key)
        for k, v in self.key_map.items():
            if k == key:
                self.app.push_view(v(self.data))
                return
        return key


class CongruenceListBox(urwid.ListBox):
    """Displays a list of CongruenceListBoxEntry objects

    list: a list of CongruenceListBoxEntry objects

    """

    def __init__(self, entries, help_string=None):
        self.entries = entries
        self.help_string = help_string
        super().__init__(urwid.SimpleFocusListWalker(self.entries))

    def keypress(self, size, key):
        log.debug("Keypress in ListBox: %s", key)
        if key == 'k':
            key = 'up'
            self.keypress(size, key)
            return
        if key == 'j':
            key = 'down'
            self.keypress(size, key)
            return
        return super().keypress(size, key)


class CongruenceFooter(urwid.Pile):
    """Represents the footer, consisting of a key map and a status line"""

    def __init__(self):
        self.key_map = urwid.AttrMap(urwid.Text("keys"), 'head')
        self.status_line = urwid.Text("", wrap='clip')
        super().__init__([self.key_map, self.status_line])

    def set_status(self, message, msgtype):
        self.status_line = urwid.AttrMap(urwid.Text(message), msgtype)


class HelpView(urwid.ListBox):
    def __init__(self, help_string):
        text = [urwid.Text(help_string)]
        super().__init__(urwid.SimpleFocusListWalker(text))


class CongruenceApp(object):
    """This class represents the app"""

    def unhandled_input(self, key):
        if key == '?':
            widget = self.get_current_widget()
            helpstr = getattr(widget, "help_string", None)
            if helpstr:
                view = HelpView(helpstr)
                self.push_view(view)
        if key == 'q':
            self.pop_view()
        if key == 'Q':
            self.exit()

    def __init__(self):
        # Set these class variables so each instance can refer to the app
        # object to use push_view/pop_view and status messages
        # TODO: static methods?
        CongruenceListBox.app = self
        CongruenceListBoxEntry.app = self
        CongruenceTreeListBox.app = self
        CongruenceTreeListBoxEntry.app = self

        # Initialize view stack
        self._view_stack = []
        self._title_stack = []

        # Create a view of all plugins defined in the config
        self.entries = []
        for name, p in config["Plugins"].items():
            title = name
            if p and "DisplayName" in p:
                title = p["DisplayName"]
            self.entries.append(
                CongruenceListBoxEntry(
                    p,
                    title,
                    {'enter': self.get_plugin_class(name)},
                ),
            )
        self.body = CongruenceListBox(self.entries, help_string=__help__)
        self.title = "Congruence"
        self.header = urwid.Text(self.title)
        self.footer = CongruenceFooter()
        self.view = urwid.Frame(
            self.body,
            header=urwid.AttrMap(self.header, 'head'),
            footer=self.footer,
        )
        self.active = True

    def get_full_title(self):
        return ' / '.join([self.title] + self._title_stack)

    def get_current_widget(self):
        return self.loop.widget.body

    def alert(self, message, msgtype='info'):
        """Show a message in the status line

        :message: the alert message as a string
        :msgtype: one of 'info', 'warning', 'error'
        """

        log.info("Alert (%s): %s" % (msgtype, message))
        self.footer.status_line.set_text((msgtype, message))

    def push_view(self, view):
        """Open a new view and keep track of the old one"""
        title = getattr(view, "title", "untitled")
        log.debug("Pushing view '%s'" % title)
        self._title_stack.append(title)
        self._view_stack.append(self.loop.widget.body)
        self.loop.widget.body = view
        self.header.set_text(('head', self.get_full_title()))

    def pop_view(self):
        """Restore the last view down the list"""

        if self._view_stack:
            view = self._view_stack.pop()
            self._title_stack.pop()
            self.loop.widget.body = view
            self.header.set_text(('head', self.get_full_title()))
        else:
            self.exit()

    def exit(self):
        self.active = False
        raise urwid.ExitMainLoop()

    def main(self):
        """Run the program."""

        self.loop = urwid.MainLoop(
            self.view,
            PALETTE,
            unhandled_input=self.unhandled_input)
        while self.active:
            try:
                self.loop.run()
            except Exception as e:
                log.exception(e)
                self.alert(str(e), 'error')

    def get_plugin_class(self, name):
        """This function retrieves the class the plugin"""

        view = getattr(
            import_module('congruence.plugins.' + name.lower()),
            "PluginView"
        )
        # TODO check for must-haves
        return view
