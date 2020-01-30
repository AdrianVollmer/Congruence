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

import urwid


class CongruenceView(object):
    def get_keymap(self):
        key_map = {
            **self.key_map,
            **self.app.key_map,
        }
        return key_map

    def selectable(self):
        return True

    def keypress(self, size, key):
        log.debug("Keypress in CongruenceView: %s" % key)
        if key in self.key_map:
            self.key_action(self.key_map[key][0], size)
            return
        return key


class RememberParentKeyMapMeta(urwid.widget.WidgetMeta):
    """This is a metaclass which keeps track of the 'key_map' class variable

    Subclasses will know what the value of key_map in its base classes were.
    """

    def __new__(cls, name, bases, attrs):
        if 'key_map' not in attrs:
            attrs['key_map'] = {}
        for b in bases:
            if hasattr(b, "key_map"):
                attrs['key_map'] = {
                    **attrs['key_map'],
                    **b.key_map,
                }
        return type.__new__(cls, name, bases, attrs)


class CongruenceTextBox(CongruenceView, urwid.ListBox,
                        metaclass=RememberParentKeyMapMeta):
    key_map = {
        'k': ('move up', 'Move up'),
        'j': ('move down', 'Move down'),
        '[': ('page up', 'Move page up'),
        ']': ('page down', 'Move page down'),
        #  '/': ('search', 'Search the list for some string'),
        #  'n': ('search next', 'Jump to the next entry in the search result'),
        #  'N': ('search prev',
        #        'Jump to the previous entry in the search result'),
    }

    def __init__(self, text):
        self.text = text
        textbox = urwid.Text(self.text)
        super().__init__(urwid.SimpleFocusListWalker([textbox]))

    def key_action(self, action, size=None):
        log.debug('Process key action "%s"' % action)
        if action == 'move down':
            urwid.ListBox.keypress(self, size, 'down')
        elif action == 'move up':
            urwid.ListBox.keypress(self, size, 'up')
        elif action == 'page down':
            urwid.ListBox.keypress(self, size, 'page down')
        elif action == 'page up':
            urwid.ListBox.keypress(self, size, 'page up')
        #  elif action == 'search':
        #      self.search()
        #  elif action == 'search next':
        #      self.search_next(1)
        #  elif action == 'search prev':
        #      self.search_next(-1)
        #  elif action == 'limit':
        #      def limit(expr):
        #          _search_results = [
        #              e for e in self.entries if e.search_match(expr)
        #          ]
        #          self.walker[:] = _search_results
        #          if expr == '.':
        #              self.app.reset_status()
        #          else:
        #              self.app.alert("To view all items, limit to '.'.",
        #                             'info')
        #      self.app.get_input(
        #          'Search for:',
        #          limit,
        #      )
        else:
            raise KeyError("Unknown key action: %s" % action)
