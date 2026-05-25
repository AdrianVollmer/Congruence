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

from __future__ import annotations

from collections.abc import Callable

import urwid

from congruence.ansiescape import translate_text_for_urwid
from congruence.keys import KEY_ACTIONS


def key_action(f: Callable) -> Callable:
    f.is_key_action = True
    return f


class CollectKeyActions(urwid.widget.WidgetMeta):
    """Metaclass that aggregates @key_action-decorated methods into key_actions."""

    def __new__(meta, name: str, bases: tuple, dct: dict) -> type:
        key_actions = [key.replace("_", " ") for key, value in dct.items() if hasattr(value, "is_key_action")]
        dct["key_actions"] = key_actions
        for b in bases:
            dct["key_actions"] += getattr(b, "key_actions", [])
        return super().__new__(meta, name, bases, dct)


class CongruenceView:
    def selectable(self) -> bool:
        return True

    def keypress(self, size: tuple, key: str) -> str | None:
        if key not in KEY_ACTIONS or KEY_ACTIONS[key] not in self.key_actions:
            return key
        action = KEY_ACTIONS[key]
        f = getattr(self, action.replace(" ", "_"), None)
        if callable(f) and f.is_key_action:
            f(size=size)
            return None
        return super().keypress(size, key)


class CongruenceTextBox(CongruenceView, urwid.ListBox, metaclass=CollectKeyActions):
    def __init__(self, text: str, color: bool = False, help_string: str | None = None) -> None:
        self.text = text
        if color and text:
            textbox_content = []
            for line in self.text.splitlines():
                textbox_content += [*translate_text_for_urwid(line), "\n"]
            textbox = urwid.Text(textbox_content)
        else:
            textbox = urwid.Text(self.text)
        self.help_string = help_string
        super().__init__(urwid.SimpleFocusListWalker([textbox]))

    @key_action
    def move_down(self, size: tuple | None = None) -> None:
        urwid.ListBox.keypress(self, size, "down")

    @key_action
    def move_up(self, size: tuple | None = None) -> None:
        urwid.ListBox.keypress(self, size, "up")

    @key_action
    def page_down(self, size: tuple | None = None) -> None:
        urwid.ListBox.keypress(self, size, "page down")

    @key_action
    def page_up(self, size: tuple | None = None) -> None:
        urwid.ListBox.keypress(self, size, "page up")

    @key_action
    def scroll_to_bottom(self, size: tuple | None = None) -> None:
        self.set_focus(0, coming_from="above")

    @key_action
    def scroll_to_top(self, size: tuple | None = None) -> None:
        self.set_focus(0, coming_from="below")
