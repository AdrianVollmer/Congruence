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

from abc import ABC, abstractmethod
import urwid

import json
import re


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


class DataObject(ABC):
    """Base class for DataObjects

    Each entry in a view has a member of this type.

    """

    def __init__(self, data):
        self._data = data
        #  log.debug(json.dumps(data, indent=2))

    @abstractmethod
    def get_title(self):
        """Subclasses who implement this must return a string"""
        pass

    @abstractmethod
    def get_columns(self):
        """Subclasses who implement this must return a list of length five

        This function is used for representing the object in a list entry.
        """
        pass

    def get_html_content(self):
        """Subclasses who implement this should return HTML in a string

        The result is passed to a CLI browser
        """
        return ""

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)

    def get_content(self):
        """Represents the body of a carded list entry"""

        return ""

    def get_head(self):
        """Represents the head of a carded list entry"""

        return self.get_title()

    def match(self, search_string):
        return (
            re.search(search_string, self.get_title())
            or re.search(search_string, self.get_content())
        )
