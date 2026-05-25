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

"""Main menu view: one entry per configured plugin."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from congruence.views.listbox import CongruenceListBox, CongruenceListBoxEntry

__help__ = """Congruence - a TUI for Confluence
    Adrian Vollmer, 2020

This is the main menu. Each entry corresponds to one plugin, which can be
configured in $XDG_CONFIG_HOME/congruence/config.yaml. Each plugin can be
used multiple times.
"""


class CongruenceMainMenu(CongruenceListBox):
    def __init__(self, plugins: list[dict]) -> None:
        entries = [MainMenuEntry(p) for p in plugins]
        super().__init__(entries, help_string=__help__)


class MainMenuEntry(CongruenceListBoxEntry):
    def __init__(self, data: dict) -> None:
        self.plugin_data = data
        title: str = data.get("DisplayName", data["PluginName"])
        super().__init__(title)

    def _get_plugin_class(self, name: str) -> type:
        module = import_module(f"congruence.plugins.{name.lower()}")
        return module.PluginView

    def get_next_view(self) -> Any:
        view_class = self._get_plugin_class(self.plugin_data["PluginName"])
        return view_class(self.plugin_data)

    def search_match(self, search_string: str) -> bool:
        return bool(search_string in str(self.plugin_data.get("DisplayName", self.plugin_data["PluginName"])))
