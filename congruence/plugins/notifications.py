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
from congruence.interface import make_request, convert_date
from congruence.views.listbox import CongruenceListBox,\
        CongruenceListBoxEntry

import json

import urwid


def get_notifications(properties={"limit": 30}):
    r = make_request("rest/mywork/latest/notification/nested",
                     params=properties,
                     )
    return json.loads(r.text)


class NotificationView(CongruenceListBox):
    def __init__(self, properties={}):
        entries = get_notifications()
        self.app.alert('Received %d items' % len(entries), 'info')

        self.title = "Notifications"
        notifications = []
        for e in entries:
            for n in e["notifications"]:
                n["reference"] = e["item"]
                n = NotificationEntry(n)
                notifications.append(n)

        super().__init__(notifications, help_string=__help__)


class NotificationEntry(CongruenceListBoxEntry):
    def __init__(self, data):
        self.data = data

        super().__init__(
            self.data,
            NotificationLine,
        )

    def get_next_view(self):
        pass


class NotificationLine(urwid.Text):
    def __init__(self, data):
        self.data = data
        date = convert_date(data["created"], "friendly")
        name = f"{data['reference']['title']}: {data['title']} ({date})"
        super().__init__(name)


PluginView = NotificationView
