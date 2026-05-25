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
from typing import ClassVar

import urwid

from congruence.args import config
from congruence.external import get_editor_input
from congruence.keys import KEY_ACTIONS, KEYS
from congruence.logging import log, log_stream
from congruence.palette import PALETTE
from congruence.views.common import CongruenceTextBox, CongruenceView
from congruence.views.mainmenu import CongruenceMainMenu


class CongruenceFooter(urwid.Pile):
    """Footer widget: key legend on top, status line below."""

    def __init__(self) -> None:
        self.key_legend = urwid.AttrMap(urwid.Text("?:help", wrap="clip"), "head")
        self.status_line = urwid.Text("", wrap="clip")
        super().__init__([self.key_legend, self.status_line], focus_item=1)

    def update_keylegend(self, key_actions: list[str]) -> None:
        text = "|".join(f"{KEYS[k][0]}:{k}" for k in key_actions)
        self.key_legend.base_widget.set_text(text)


class CongruenceInput(urwid.Edit):
    """Edit widget that emits a 'done' signal on Enter."""

    signals: ClassVar[list[str]] = ["done"]

    def keypress(self, size: tuple, key: str) -> str | None:
        if key == "enter":
            urwid.emit_signal(self, "done", self, self.get_edit_text())
            super().set_edit_text("")
            return None
        return urwid.Edit.keypress(self, size, key)


class HelpView(CongruenceTextBox):
    """Help overlay built from widget metadata and key actions."""

    title = "Help"

    def __init__(self, widget: CongruenceView, extra_actions: list[str]) -> None:
        help_string = getattr(widget, "help_string", "") or ""
        key_legend = "\nKey map:\n"
        for action in widget.key_actions + extra_actions:
            key = KEYS[action][0]
            description = KEYS[action][1]
            display_key = "space" if key == " " else key
            key_legend += f"    {display_key}: {description}\n"
        super().__init__(help_string + key_legend)


class CongruenceApp:
    """Top-level application object."""

    key_actions: ClassVar[list[str]] = ["show help", "back", "exit", "show log"]

    def unhandled_input(self, key: str) -> None:
        if key not in KEY_ACTIONS:
            return
        action = KEY_ACTIONS[key]
        if action == "show help":
            widget = self.get_current_widget()
            if isinstance(widget, HelpView):
                return
            self.push_view(HelpView(widget, self.key_actions))
        elif action == "back":
            self.pop_view()
        elif action == "exit":
            self.exit()
        elif action == "show log":
            log_text = log_stream.getvalue()
            log.debug(log_text)
            view = CongruenceTextBox(log_text)
            view.title = "Log"
            self.push_view(view)

    def __init__(self) -> None:
        global app
        app = self
        CongruenceView.app = self

        self._view_stack: list = []
        self._title_stack: list[str] = []

        self.body = CongruenceMainMenu(config["Plugins"])
        self.title = "Congruence"
        self.header = urwid.Text(self.title)
        self.footer = CongruenceFooter()
        self.view = urwid.Frame(
            self.body,
            header=urwid.AttrMap(self.header, "head"),
            footer=self.footer,
        )
        self.footer.update_keylegend(self.body.key_actions)
        self.active = True

    def get_full_title(self) -> str:
        return " / ".join([self.title, *self._title_stack])

    def get_current_widget(self) -> CongruenceView:
        return self.loop.widget.body

    def alert(self, message: str, msgtype: str = "info") -> None:
        """Display *message* in the status line with style *msgtype*."""
        log.info(f"Alert ({msgtype}): {message}")
        self.footer.status_line.set_text((msgtype, message))
        try:
            self.loop.draw_screen()
        except AssertionError:
            pass

    def reset_status(self) -> None:
        self.footer.status_line.set_text(("info", ""))
        try:
            self.loop.draw_screen()
        except AssertionError:
            pass

    def get_input(self, prompt: str, callback: Callable[[str], None]) -> None:
        """Show an inline edit field in the footer and call *callback* on Enter."""
        footer = self.view.get_footer().widget_list[1]

        def handler(widget: urwid.Edit, text: str) -> None:
            self.view.get_footer().widget_list[1] = footer
            self.view.set_focus("body")
            callback(text)

        edit = CongruenceInput(caption=prompt + " ")
        self.view.get_footer().widget_list[1] = edit
        urwid.connect_signal(edit, "done", handler)
        self.view.set_focus("footer")

    def get_long_input(self, prompt: str = "") -> str:
        """Open an external editor and return the stripped, non-comment lines."""
        result = get_editor_input(prompt)
        self.loop.screen.clear()
        lines = [line.strip() for line in result.splitlines() if not line.startswith("##")]
        return "\n".join(lines).strip()

    def push_view(self, view: CongruenceView) -> None:
        """Push *view* onto the view stack."""
        title = getattr(view, "title", "untitled")
        log.debug(f"Pushing view '{title}'")
        self._title_stack.append(title)
        self._view_stack.append(self.loop.widget.body)
        self.loop.widget.body = view
        self.header.set_text(("head", self.get_full_title()))
        self.footer.update_keylegend(view.key_actions)

    def pop_view(self) -> None:
        """Restore the previous view, or exit if the stack is empty."""
        if self._view_stack:
            view = self._view_stack.pop()
            self._title_stack.pop()
            self.loop.widget.body = view
            self.header.set_text(("head", self.get_full_title()))
            self.footer.update_keylegend(view.key_actions)
        else:
            self.exit()

    def exit(self) -> None:
        self.active = False
        raise urwid.ExitMainLoop()

    def main(self) -> None:
        """Run the urwid event loop, restarting after caught exceptions."""
        self.loop = urwid.MainLoop(self.view, PALETTE, unhandled_input=self.unhandled_input)
        while self.active:
            try:
                self.loop.run()
            except Exception as e:
                log.exception(e)
                self.alert(f"{type(e).__name__}: {e}", "error")
