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


#  from congruence.args import config
#  from congruence.palette import PALETTE
from congruence.logging import log
from congruence.views.common import CongruenceView, RememberParentKeyMapMeta

import urwid


class CongruenceListBox(CongruenceView, urwid.ListBox,
                        metaclass=RememberParentKeyMapMeta):
    """Displays a list of CongruenceListBoxEntry objects

    :entries: a list of CongruenceListBoxEntry objects

    """

    key_map = {
        'k': ('move up', 'move up'),
        'j': ('move down', 'move down'),
        '[': ('page up', 'move page up'),
        ']': ('page down', 'move page down'),
        'enter': ('next view', 'Enter next view'),
        'd': ('show details', 'Show details about the focused item'),
    }

    def __init__(self, entries, help_string=None):
        self.entries = entries
        self.help_string = help_string
        self.walker = urwid.SimpleFocusListWalker(self.entries)
        super().__init__(self.walker)

    def redraw(self):
        self.walker[:] = self.entries

    def key_action(self, action, size=None):
        log.debug('key_action %s' % action)
        if action == 'move down':
            urwid.ListBox.keypress(self, size, 'down')
        elif action == 'move up':
            urwid.ListBox.keypress(self, size, 'up')
        elif action == 'page down':
            urwid.ListBox.keypress(self, size, 'page down')
        elif action == 'page up':
            urwid.ListBox.keypress(self, size, 'page up')
        elif action == 'next view':
            view = self.get_focus()[0].get_next_view()
            if view:
                self.app.push_view(view)
        else:
            raise KeyError("Unknown key action: %s" % action)


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
                self.app.push_view(v[0](self.data))
                return
        return key

    def get_next_view(self):
        pass
