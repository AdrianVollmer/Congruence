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
from congruence.keys import KEYS, KEY_ACTIONS
from congruence.logging import log
from congruence.views.mainmenu import CongruenceMainMenu
from congruence.views.common import CongruenceView, CongruenceTextBox
from congruence.external import get_editor_input

import urwid


class CongruenceFooter(urwid.Pile):
    """Represents the footer, consisting of a key map and a status line"""

    def __init__(self):
        self.key_legend = urwid.AttrMap(urwid.Text("?:help", wrap='clip'),
                                        'head')
        self.status_line = urwid.Text("", wrap='clip')
        super().__init__([self.key_legend, self.status_line], focus_item=1)

    def update_keylegend(self, key_actions):
        text = '|'.join("%s:%s" % (KEYS[k][0], k) for k in key_actions)
        self.key_legend.base_widget.set_text(text)


class CongruenceInput(urwid.Edit):
    """An Edit widget with an extra signal"""

    signals = ['done']

    def keypress(self, size, key):
        if key == 'enter':
            urwid.emit_signal(self, 'done',
                              self, self.get_edit_text())
            super().set_edit_text('')
            return
        return urwid.Edit.keypress(self, size, key)


class HelpView(CongruenceTextBox):
    """Builds a view based on the metadata of a widget

    :widget: an object of type XYZ
    """
    title = "Help"

    def __init__(self, widget):
        help_string = getattr(widget, "help_string", "") or ""
        key_legend = "\nKey map:\n"
        for action in widget.get_actions():
            key = KEYS[action][0]
            description = KEYS[action][1]
            if key == ' ':
                # Replace ' '  with 'space'
                key_legend += f"    space: {description}\n"
            else:
                key_legend += f"    {key}: {description}\n"
        text = help_string+key_legend
        super().__init__(text)


class CongruenceApp(object):
    """This class represents the app"""

    key_actions = ['show help', 'back', 'exit']

    def unhandled_input(self, key):
        if key not in KEY_ACTIONS:
            return
        if KEY_ACTIONS[key] == 'show help':
            widget = self.get_current_widget()
            if isinstance(widget, HelpView):
                # HelpViews don't need help
                return
            view = HelpView(widget)
            self.push_view(view)
        elif KEY_ACTIONS[key] == 'back':
            self.pop_view()
        elif KEY_ACTIONS[key] == 'exit':
            self.exit()

    def __init__(self):
        # Set these class variables so each instance can refer to the app
        # object to use push_view/pop_view and status messages
        # TODO: static methods?
        global app
        app = self
        CongruenceView.app = self

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
        self.footer.update_keylegend(self.body.key_actions)
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

    def reset_status(self):
        self.footer.status_line.set_text(('info', ''))

    def get_input(self, prompt, callback):
        """Get user input in an Edit field in the footer"""

        footer = self.view.get_footer().widget_list[1]

        def handler(widget, text):
            self.view.get_footer().widget_list[1] = footer
            self.view.set_focus('body')
            callback(text)
        edit = CongruenceInput(caption=prompt + " ")
        self.view.get_footer().widget_list[1] = edit
        urwid.connect_signal(edit, 'done', handler)
        self.view.set_focus('footer')

    def get_long_input(self, prompt=""):
        """Open an external editor to get user input"""

        result = get_editor_input(prompt)
        self.loop.screen.clear()
        result = result.splitlines()
        result = [line for line in result if not line.startswith('##')]
        return '\n'.join(result)

    def push_view(self, view):
        """Open a new view and keep track of the old one"""

        title = getattr(view, "title", "untitled")
        log.debug("Pushing view '%s'" % title)
        self._title_stack.append(title)
        self._view_stack.append(self.loop.widget.body)
        self.loop.widget.body = view
        self.header.set_text(('head', self.get_full_title()))
        self.footer.update_keylegend(view.key_actions)

    def pop_view(self):
        """Restore the last view down the list"""

        if self._view_stack:
            view = self._view_stack.pop()
            self._title_stack.pop()
            self.loop.widget.body = view
            self.header.set_text(('head', self.get_full_title()))
            self.footer.update_keylegend(view.key_actions)
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
        #  self.loop.run()
        while self.active:
            try:
                self.loop.run()
            except Exception as e:
                log.exception(e)
                self.alert("%s: %s" % (type(e).__name__, str(e)), 'error')
