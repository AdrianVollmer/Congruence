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

from congruence.keys import KEY_ACTIONS
#  from congruence.logging import log
from congruence.ansiescape import translate_text_for_urwid

import urwid


def key_action(f):
    """Decorator that promotes a function to a key action"""
    f.is_key_action = True
    return f


class CollectKeyActions(urwid.widget.WidgetMeta):
    """This metaclass creates a list of all key actions

    Key actions must be marked with the @key_action decorator. It also
    appends all key actions of all base classes.
    """
    def __new__(meta, name, bases, dct):
        key_actions = []
        for key, value in dct.items():
            if hasattr(value, 'is_key_action'):
                key_actions.append(key.replace('_', ' '))
        dct['key_actions'] = key_actions
        for b in bases:
            dct['key_actions'] += getattr(b, 'key_actions', [])
        return super().__new__(meta, name, bases, dct)


class CongruenceView(object):
    def selectable(self):
        return True

    def keypress(self, size, key):
        if (
            key not in KEY_ACTIONS
            or KEY_ACTIONS[key] not in self.key_actions
        ):
            return key
        action = KEY_ACTIONS[key]
        f = getattr(self, action.replace(' ', '_'), None)
        if callable(f) and f.is_key_action:
            f(size=size)
            return
        return super().keypress(size, key)


class CongruenceTextBox(CongruenceView, urwid.ListBox,
                        metaclass=CollectKeyActions):
    def __init__(self, text, color=False, help_string=None):
        self.text = text
        if color and text:
            textbox = []
            for l in self.text.splitlines():
                textbox += translate_text_for_urwid(l) + ['\n']
            textbox = urwid.Text(textbox)
        else:
            textbox = urwid.Text(self.text)
        self.help_string = help_string
        super().__init__(urwid.SimpleFocusListWalker([textbox]))

    @key_action
    def move_down(self, size=None):
        urwid.ListBox.keypress(self, size, 'down')

    @key_action
    def move_up(self, size=None):
        urwid.ListBox.keypress(self, size, 'up')

    @key_action
    def page_down(self, size=None):
        urwid.ListBox.keypress(self, size, 'page down')

    @key_action
    def page_up(self, size=None):
        urwid.ListBox.keypress(self, size, 'page up')

    @key_action
    def scroll_to_bottom(self, size=None):
        self.set_focus(0, coming_from='above')

    @key_action
    def scroll_to_top(self, size=None):
        self.set_focus(0, coming_from='below')
