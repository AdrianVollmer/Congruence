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

from congruence.interface import make_request
from congruence.views import ConfluenceMainView, ConfluenceListBox,\
        ConfluenceSimpleListEntry

import json


def get_notifications(props={"limit": 30}):
    r = make_request("rest/mywork/latest/notification/nested",
                     params=props,
                     )
    return json.loads(r.text)


class PluginView(ConfluenceMainView):
    def __init__(self, props={}):
        def body_builder():
            entries = get_notifications()

            notifications = []
            for e in entries:
                for n in e["notifications"]:
                    n["reference"] = e["item"]
                    notifications.append(n)

            notifications = [ConfluenceNotificationEntry(n)
                             for n in notifications]

            return ConfluenceListBox(notifications)
        super().__init__(body_builder, "Notifications")


class ConfluenceNotificationEntry(ConfluenceSimpleListEntry):
    def __init__(self, data):
        name = f"{data['reference']['title']}: {data['title']}"
        view = None
        super().__init__(name, view)
