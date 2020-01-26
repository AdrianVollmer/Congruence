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


from congruence.args import config
from congruence.palette import PALETTE
from congruence.logging import log
from congruence.views.mainmenu import CongruenceMainMenu
from congruence.views.listbox import CongruenceListBox
from congruence.views.treelistbox import CongruenceTreeListBox

import urwid


class CongruenceFooter(urwid.Pile):
    """Represents the footer, consisting of a key map and a status line"""

    def __init__(self):
        self.key_legend = urwid.AttrMap(urwid.Text("keys"), 'head')
        self.status_line = urwid.Text("", wrap='clip')
        super().__init__([self.key_legend, self.status_line], focus_item=1)

    def set_status(self, message, msgtype):
        self.status_line = urwid.AttrMap(urwid.Text(message), msgtype)


class CongruenceInput(urwid.Edit):
    signals = ['done']

    def keypress(self, size, key):
        if key == 'enter':
            urwid.emit_signal(self, 'done',
                              self, self.get_edit_text())
            super().set_edit_text('')
            return
        return urwid.Edit.keypress(self, size, key)


class HelpView(urwid.ListBox):
    """Builds a view based on the metadata of a widget

    :widget: an object of type XYZ
    """
    title = "Help"

    def __init__(self, widget):
        help_string = getattr(widget, "help_string", "")
        key_legend = "\nKey map:\n"
        for k, v in widget.get_keymap().items():
            if k == ' ':
                # Replace ' '  with 'space'
                key_legend += f"    space: {v[1]}\n"
            else:
                key_legend += f"    {k}: {v[1]}\n"
        text = [urwid.Text(help_string+key_legend)]
        super().__init__(urwid.SimpleFocusListWalker(text))


class CongruenceApp(object):
    """This class represents the app"""

    def unhandled_input(self, key):
        if key == '?':
            widget = self.get_current_widget()
            view = HelpView(widget)
            self.push_view(view)
        if key == 'q':
            self.pop_view()
        if key == 'Q':
            self.exit()

    def __init__(self):
        # Set these class variables so each instance can refer to the app
        # object to use push_view/pop_view and status messages
        # TODO: static methods?
        global app
        app = self
        CongruenceListBox.app = self
        CongruenceTreeListBox.app = self

        # Initialize view stack
        self._view_stack = []
        self._title_stack = []

        self.body = CongruenceMainMenu(config["Plugins"])
        self.title = "Congruence"
        self.header = urwid.Text(self.title)
        self.footer = CongruenceFooter()
        self.view = urwid.Frame(
            self.body,
            header=urwid.AttrMap(self.header, 'head'),
            footer=self.footer,
        )
        self.active = True

    def get_full_title(self):
        return ' / '.join([self.title] + self._title_stack)

    def get_current_widget(self):
        return self.loop.widget.body

    def alert(self, message, msgtype='info'):
        """Show a message in the status line

        :message: the alert message as a string
        :msgtype: one of 'info', 'warning', 'error'
        """

        log.info("Alert (%s): %s" % (msgtype, message))
        self.footer.status_line.set_text((msgtype, message))

    def get_input(self, prompt, callback):
        footer = self.view.get_footer().widget_list[1]

        def handler(widget, text):
            self.view.get_footer().widget_list[1] = footer
            self.view.set_focus('body')
            callback(text)
        edit = CongruenceInput(caption=prompt + " ")
        self.view.get_footer().widget_list[1] = edit
        urwid.connect_signal(edit, 'done', handler)
        self.view.set_focus('footer')

    def push_view(self, view):
        """Open a new view and keep track of the old one"""
        title = getattr(view, "title", "untitled")
        log.debug("Pushing view '%s'" % title)
        self._title_stack.append(title)
        self._view_stack.append(self.loop.widget.body)
        self.loop.widget.body = view
        self.header.set_text(('head', self.get_full_title()))

    def pop_view(self):
        """Restore the last view down the list"""

        if self._view_stack:
            view = self._view_stack.pop()
            self._title_stack.pop()
            self.loop.widget.body = view
            self.header.set_text(('head', self.get_full_title()))
        else:
            self.exit()

    def exit(self):
        self.active = False
        raise urwid.ExitMainLoop()

    def main(self):
        """Run the program."""

        self.loop = urwid.MainLoop(
            self.view,
            PALETTE,
            unhandled_input=self.unhandled_input)
        while self.active:
            try:
                self.loop.run()
            except Exception as e:
                log.exception(e)
                self.alert("%s: %s" % (type(e).__name__, str(e)), 'error')
