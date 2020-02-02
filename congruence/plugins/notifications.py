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

__help__ = """Confluence Notifications

This view displays your latest notifications.

"""
from congruence.interface import make_request, convert_date, html_to_text
from congruence.views.common import CongruenceTextBox
from congruence.views.listbox import CongruenceListBox,\
        CongruenceListBoxEntry
from congruence.objects import ContentObject
from congruence.logging import log

import json


class NotificationView(CongruenceListBox):
    key_actions = ['load more']

    def __init__(self, properties={}):
        self.title = "Notifications"
        self.limit = 20

        if 'Limit' in properties:
            self.limit = properties["Limit"]
        self.entries = self.get_notifications()

        super().__init__(self.entries, help_string=__help__)

    def get_notifications(self, before=None):
        params = {
            'limit': self.limit,
        }
        if before:
            params['before'] = before

        log.debug(params)
        r = make_request("rest/mywork/latest/notification",
                         params=params,
                         )
        entries = r.json()
        notifications = []
        for e in entries:
            n = NotificationEntry(NotificationObject(e), cols=True)
            notifications.append(n)
        self.app.alert('Received %d items' % len(notifications), 'info')
        return notifications

    def ka_load_more(self, size=None):
        last = self.entries[-1].obj._data['id']
        self.entries += self.get_notifications(before=last)
        self.redraw()


class NotificationEntry(CongruenceListBoxEntry):
    def get_next_view(self):
        text = self.obj.get_title() + '\n'

        if 'title' in self.obj._data:
            text += "Title: %s\n" % self.obj._data['item']['title']
        text += "Created: %s\n" % convert_date(self.obj._data['created'])
        if not self.obj._data['created'] == self.obj._data['updated']:
            text += "Updated: %s\n" % convert_date(self.obj._data['updated'])

        if 'highlightText' in self.obj.metadata:
            text += ("\n> %s\n" %
                     self.obj.metadata['highlightText'])

        if 'description' in self.obj._data:
            text += "\n%s\n" % html_to_text(self.obj._data['description'])
        return CongruenceTextBox(text)

    def get_details_view(self):
        text = self.obj.get_json()
        return CongruenceTextBox(text)

    def search_match(self, search_string):
        return self.obj.match(search_string)


class NotificationObject(ContentObject):
    def __init__(self, data):
        self._data = data
        self.metadata = self._data['metadata']
        try:
            self.title = self._data['item']['title']
        except KeyError:
            self.title = self._data["title"]

    # TODO get_title should be called get_display_title or something
    def get_title(self, cols=False):
        try:
            entity = self._data['entity'][0].upper()
        except KeyError:
            entity = "?"
        if self.metadata:
            user = self.metadata['user']
            action = self._data['action']
        else:
            user = "?"
            action = "?"
        if cols:
            return [
                entity,
                user,
                action,
                convert_date(self._data['updated'], 'friendly'),
                self.title,
            ]
        return self.title

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)


PluginView = NotificationView
