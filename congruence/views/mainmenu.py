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


"""
This file contains general 'views' (i.e. urwid widgets) which are
particular to this app and not to Confluence
"""

__help__ = """About Congruence:
    Adrian Vollmer, 2020

Main menu
"""

from congruence.views.listbox import CongruenceListBox, \
        CongruenceListBoxEntry
#  from congruence.logging import log

from importlib import import_module

import urwid


class CongruenceMainMenu(CongruenceListBox):

    def __init__(self, plugins):
        # Create a view of all plugins defined in the config
        self.entries = []
        for p in plugins:
            self.entries.append(MainMenuEntry(p))
        #  self.body = CongruenceListBox(self.entries, help_string=__help__)
        super().__init__(self.entries, help_string=__help__)


class MainMenuEntry(CongruenceListBoxEntry):
    def __init__(self, data):
        self.plugin_data = data
        title = data["PluginName"]
        if "DisplayName" in data:
            title = data['DisplayName']
        # this now overwrite self.data
        return super().__init__(title, urwid.Text)

    def get_plugin_class(self, name):
        """This function retrieves the class the plugin"""

        view = getattr(
            import_module('congruence.plugins.' + name.lower()),
            "PluginView"
        )
        # TODO check for must-haves
        return view

    def get_next_view(self):
        viewClass = self.get_plugin_class(self.plugin_data['PluginName'])
        return viewClass(self.plugin_data)
