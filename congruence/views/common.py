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
from congruence.keys import KEY_ACTIONS
from congruence.ansiescape import translate_text_for_urwid

import urwid


class CongruenceView(object):
    def get_actions(self):
        key_actions = self.key_actions + self.app.key_actions
        return key_actions

    def selectable(self):
        return True

    def keypress(self, size, key):
        log.debug("Keypress in CongruenceView: %s" % key)
        if (
            key not in KEY_ACTIONS
            or KEY_ACTIONS[key] not in self.key_actions
        ):
            return key
        action = KEY_ACTIONS[key]
        f = getattr(self, 'ka_' + action.replace(' ', '_'), None)
        if callable(f):
            f(size=size)
            return
        return super().keypress(size, key)


class RememberParentKeyMapMeta(urwid.widget.WidgetMeta):
    """This is a metaclass which keeps track of the 'key_actions' class variable

    Subclasses will know what the value of key_actions in its base classes
    were.
    """

    def __new__(cls, name, bases, attrs):
        if 'key_actions' not in attrs:
            attrs['key_actions'] = []
        for b in bases:
            if hasattr(b, "key_actions"):
                attrs['key_actions'] += b.key_actions
        return type.__new__(cls, name, bases, attrs)


class CongruenceTextBox(CongruenceView, urwid.ListBox,
                        metaclass=RememberParentKeyMapMeta):
    key_actions = [
        'move up',
        'move down',
        'page up',
        'page down',
        'scroll to bottom',
        'scroll to top',
    ]

    def __init__(self, text, color=False):
        self.text = text
        if color and text:
            textbox = []
            for l in self.text.splitlines():
                textbox += translate_text_for_urwid(l) + ['\n']
            textbox = urwid.Text(textbox)
        else:
            textbox = urwid.Text(self.text)
        super().__init__(urwid.SimpleFocusListWalker([textbox]))

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
