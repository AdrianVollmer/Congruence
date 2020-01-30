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


from congruence.logging import log

import urwid


class CongruenceTextBox(urwid.Widget):
    pass


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
