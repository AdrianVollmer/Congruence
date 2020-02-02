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


def get_notifications(properties={"limit": 30}):
    r = make_request("rest/mywork/latest/notification/nested",
                     params=properties,
                     )
    return r.json()


class NotificationView(CongruenceListBox):
    def __init__(self, properties={}):
        entries = get_notifications()
        self.app.alert('Received %d items' % len(entries), 'info')

        self.title = "Notifications"
        notifications = []
        for e in entries:
            for n in e["notifications"]:
                n["reference"] = e["item"]
                n = NotificationEntry(NotificationObject(n), cols=True)
                notifications.append(n)

        super().__init__(notifications, help_string=__help__)


class NotificationEntry(CongruenceListBoxEntry):
    def get_next_view(self):
        text = self.obj.get_title() + '\n'

        if 'title' in self.obj.ref:
            text += "Title: %s\n" % self.obj.ref['title']
        if 'highlightText' in self.obj.metadata:
            text += ("Highlighted text: %s\n" %
                     self.obj.metadata['highlightText'])

        text += "Created: %s\n" % convert_date(self.obj._data['created'])
        if not self.obj._data['created'] == self.obj._data['updated']:
            text += "Updated: %s\n" % convert_date(self.obj._data['updated'])

        if 'description' in self.obj._data:
            text += "\n%s\n" % html_to_text(self.obj._data['description'])
        return CongruenceTextBox(text)

    def get_details_view(self):
        text = self.obj.get_json()
        return CongruenceTextBox(text)


class NotificationObject(ContentObject):
    def __init__(self, data):
        self._data = data
        self.metadata = self._data['metadata']
        self.ref = self._data['reference']

    def get_title(self, cols=False):
        log.debug(self._data)
        try:
            entity = self.ref['entity'][0].upper()
        except KeyError:
            entity = "?"
        if self.metadata:
            user = self.metadata['user']
            action = self.ref['action']
        else:
            user = "?"
            action = "?"
        if cols:
            return [
                entity,
                user,
                action,
                convert_date(self._data['updated'], 'friendly'),
                self.ref['title'],
            ]
        return (
            self._data["title"]
            + " (" + convert_date(self._data['updated'], 'friendly')
            + ")"
        )

    def get_json(self):
        return json.dumps(self._data, indent=2, sort_keys=True)


PluginView = NotificationView
