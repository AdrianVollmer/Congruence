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
from typing import TYPE_CHECKING, Any, ClassVar, cast

import urwid

from congruence.ansiescape import translate_text_for_urwid
from congruence.keys import KEY_ACTIONS

if TYPE_CHECKING:
    from congruence.app import CongruenceApp


def key_action(f: Callable) -> Callable:
    f.is_key_action = True  # type: ignore[attr-defined]
    return f


class CollectKeyActions(urwid.widget.WidgetMeta):
    """Metaclass that aggregates @key_action-decorated methods into key_actions."""

    def __new__(cls, name: str, bases: tuple, dct: dict) -> type:
        key_actions = [key.replace("_", " ") for key, value in dct.items() if hasattr(value, "is_key_action")]
        dct["key_actions"] = key_actions
        for b in bases:
            dct["key_actions"] += getattr(b, "key_actions", [])
        return super().__new__(cls, name, bases, dct)


class CongruenceView:
    app: ClassVar[CongruenceApp]  # injected by CongruenceApp.__init__
    key_actions: ClassVar[list[str]]  # populated by CollectKeyActions metaclass
    title: str
    help_string: str | None

    def selectable(self) -> bool:
        return True

    def keypress(self, size: tuple[int, ...], key: str) -> str | None:
        if key not in KEY_ACTIONS or KEY_ACTIONS[key] not in self.key_actions:
            return key
        action = KEY_ACTIONS[key]
        f = getattr(self, action.replace(" ", "_"), None)
        if callable(f) and getattr(f, "is_key_action", False):
            f(size=size)
            return None
        return super().keypress(size, key)  # type: ignore[misc]


class CongruenceTextBox(CongruenceView, urwid.ListBox, metaclass=CollectKeyActions):
    def __init__(self, text: Any, color: bool = False, help_string: str | None = None) -> None:
        self.title: str = getattr(self, "title", "")
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
    def move_down(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "down")

    @key_action
    def move_up(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "up")

    @key_action
    def page_down(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "page down")

    @key_action
    def page_up(self, size: tuple[int, ...] | None = None) -> None:
        urwid.ListBox.keypress(self, cast("tuple[int, int]", size or (0, 0)), "page up")

    @key_action
    def scroll_to_bottom(self, size: tuple | None = None) -> None:
        self.set_focus(0, coming_from="above")

    @key_action
    def scroll_to_top(self, size: tuple | None = None) -> None:
        self.set_focus(0, coming_from="below")
