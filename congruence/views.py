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

__help__ = """About Congruence:
    Adrian Vollmer, 2020

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus non risus
pellentesque, tincidunt risus in, tempor quam. Vestibulum fermentum lectus
nisi, at tristique quam sollicitudin ut. Fusce viverra faucibus viverra. Sed
nec sagittis enim. Mauris bibendum sem sit amet placerat malesuada. Sed elit
dolor, facilisis ut consequat eu, fermentum id arcu. Suspendisse pretium
sagittis dignissim. Fusce non elit massa. Pellentesque vestibulum sem id
urna interdum, nec dapibus lectus pellentesque.

Suspendisse eget accumsan magna. Pellentesque ut nunc vitae quam faucibus
porta. Suspendisse quis ipsum ut lacus ultricies porttitor eget vel lacus.
Vivamus eget nisl eu sapien tristique dapibus nec et mauris. Donec eu
iaculis tortor. Cras ornare arcu quis quam viverra, at varius odio rutrum.
Proin commodo tempor felis at sagittis. Vivamus sit amet nisi at tortor
ultrices condimentum id non odio. Maecenas nec libero velit. Sed sodales
fringilla eros eget congue. Vestibulum ligula urna, vulputate a arcu ac,
viverra convallis neque. Suspendisse tristique lacus feugiat volutpat
tristique.

Duis consequat elementum turpis. Maecenas eget sem eu eros commodo vehicula
at semper sem. Duis scelerisque cursus lorem non accumsan. Vestibulum dictum
magna vestibulum varius pretium. Suspendisse viverra ornare nulla vel
vehicula. Curabitur est lectus, fermentum non convallis non, tempor quis
ligula. Sed molestie placerat dignissim. Etiam justo lorem, blandit a
interdum sit amet, consectetur eget tortor. Suspendisse finibus urna in
commodo pulvinar. Praesent in sapien in mi sagittis lacinia ac at neque.
Curabitur ultricies dui quis eleifend ultrices. Donec feugiat convallis
porttitor. Donec ullamcorper arcu consectetur eleifend facilisis. Nullam
quis blandit massa. Sed at tellus porttitor, ultricies massa eget, convallis
libero.

Integer sed augue libero. Pellentesque scelerisque libero dui, vel venenatis
sapien congue eu. Proin feugiat quis ligula sed pulvinar. Ut nec commodo
lacus. Nam pulvinar, magna sed feugiat dignissim, metus nisl finibus lectus,
vitae fermentum massa sapien quis erat. Nunc vel lacinia sem. Etiam vitae
fermentum ligula. Quisque vitae dolor pretium ante accumsan gravida eu eget
quam. Integer semper lectus at quam maximus, eu malesuada enim placerat.
Donec feugiat mi neque, quis egestas justo fringilla et. Nullam bibendum
interdum purus, eu vehicula odio ullamcorper non.

Ut gravida pellentesque efficitur. Fusce imperdiet sapien nibh, eu feugiat
ex laoreet vitae. Proin accumsan metus ante, at mollis dolor vestibulum in.
Phasellus viverra faucibus justo vel cursus. Aliquam vehicula, urna tempus
auctor interdum, nisi tortor pellentesque lectus, ut vulputate justo massa
quis risus. Aenean ex arcu, mattis ut ante eu, pulvinar ultrices nibh. Nam
at luctus lacus. Quisque blandit, risus et vestibulum pharetra, sapien nisl
pellentesque dolor, et tempor nisi mauris id felis. Quisque et tempor odio.
Proin quis risus nunc. Donec vel fermentum est, nec sodales est. Curabitur
vitae orci mauris. Aliquam ullamcorper gravida nunc, nec scelerisque ex
varius quis. Pellentesque vel magna eu eros volutpat dignissim a sit amet
lorem. Aenean nulla elit, facilisis at purus non, interdum consequat massa.
Suspendisse fringilla arcu nisi, eget viverra metus congue vitae.  """

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


class ConfluenceSimpleListEntry(urwid.WidgetWrap):
    """Represents one item in a ListBox

    text: can be a string or a list of strings. If it is a list, the item
        will be separated into columns.
    """

    def __init__(self, text, view=None):
        self.view = view
        self.text = text
        if isinstance(self.text, str):
            line = urwid.Text(self.text)
        else:
            line = urwid.Columns(
                [('pack', urwid.Text(t)) for t in text],
                dividechars=1
            )
        widget = urwid.AttrMap(
            line,
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
    """Displays a list of ConfluenceSimpleListEntry objects

    list: a list of ConfluenceSimpleListEntry objects

    """

    def __init__(self, entries):
        self.entries = entries
        super().__init__(urwid.SimpleFocusListWalker(self.entries))


class ConfluenceMainView(urwid.Frame):
    """Represents the main view of the app

    Every plugin should subclass this view.

    body_builder: A function, which takes no arguments and returns a
        urwid.Widget which implemented get_focus(). This widget can have a
        'view' attribute of type ConfluenceMainView, which will be shown
        when 'enter' is pressed.
    title_text: an optional text for the header
    footer_text: an optional text for the footer
    """

    def __init__(self, body_builder,
                 title_text="",
                 footer_text="",
                 help_string=__help__):
        self.body_builder = body_builder
        self.title_text = title_text
        self.footer_text = footer_text
        self.footer = urwid.AttrWrap(urwid.Text(self.footer_text), 'foot')
        self.header = urwid.AttrWrap(urwid.Text(self.title_text), 'head')
        self.help_string = help_string

    def build(self):
        self.view = self.body_builder()
        if self.view:
            super().__init__(
                self.view,
                footer=self.footer,
                header=self.header,
            )
            return self
        return None

    def build_help(self):
        def body_builder():
            text = [urwid.Text(self.help_string)]
            view = urwid.ListBox(urwid.SimpleFocusListWalker(text))
            return view
        return ConfluenceMainView(
            body_builder,
            title_text="Help: " + self.title_text,
        ).build()

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
        if key == "?":
            if self.help_string:
                next_view = self.build_help()
                self.app.push_view(next_view)
                return None
        if key == 'k':
            key = 'up'
            self.view.keypress(size, key)
            return
        if key == 'j':
            key = 'down'
            self.view.keypress(size, key)
            return
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
            "Congruence main menu",
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
            raise urwid.ExitMainLoop()

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
            import_module('congruence.plugins.' + name.lower()),
            "PluginView"
        )
        return view(props=props)
