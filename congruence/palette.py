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


PALETTE = [
    ('body', 'default', 'dark gray'),
    ('focus', 'black', 'brown'),
    ('head', 'yellow', 'black', 'standout'),
    ('card-head', 'light gray', 'black'),
    ('card-focus', 'black', 'brown'),
    ('foot', 'light gray', 'black'),
    ('title', 'white', 'black', 'bold'),
    ('flag', 'dark gray', 'light gray'),
    ('error', 'dark red', 'default'),
    ('info', 'dark blue', 'default'),
    ('warning', 'yellow', 'default'),
]


for i, p in enumerate(PALETTE):
    if 'Palette' in config and p[0] in config['Palette']:
        PALETTE[i] = (
            p[0],
            config['Palette'][p[0]]['Foreground'],
            config['Palette'][p[0]]['Background'],
        )
