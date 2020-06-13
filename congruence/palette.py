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

import congruence.environment as env


PALETTE = [
    ('body', 'default', 'default'),
    ('focus', 'black', 'brown'),
    ('head', 'yellow', 'black', 'standout'),
    ('foot', 'light gray', 'black'),
    ('card-head', 'default, bold', 'black'),
    ('card-focus', 'black', 'brown'),
    ('error', 'dark red', 'default'),
    ('info', 'dark blue', 'default'),
    ('warning', 'yellow', 'default'),
]


for i, p in enumerate(PALETTE):
    if 'Palette' in env.config and p[0] in env.config['Palette']:
        PALETTE[i] = (
            p[0],
            env.config['Palette'][p[0]]['Foreground'],
            env.config['Palette'][p[0]]['Background'],
        )
