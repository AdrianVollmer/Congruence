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
from congruence.logging import log


# action: (key, description)
KEYS = {
    'move up': ('k', "Move up"),
    'move down': ('j', "Move down"),
    'page up': ('[', "Move page up"),
    'page down': (']', "Move page down"),
    'scroll to top': ('g', "Scroll to the top of this view"),
    'scroll to bottom': ('G', "Scroll to the bottom of this view"),
    'search': ('/', "Search the list for some string"),
    'search next': ('n', "Jump to the next entry in the search result"),
    'search prev': ('N', "Jump to the previous entry in the search result"),
    'limit': ('l', "Limit entries matching some string"),
    'next view': ('enter', "Enter next view"),
    'cycle next': ('J', "Cycle views forward"),
    'cycle prev': ('K', "Cycle views backward"),
    'show details': ('d', "Show details about the focused item"),
    'toggle collapse': (' ', "Collapse the tree at the focused item"),
    'show help': ('?', "Show a description of what you are seeing"
                  " together with the key map for the current view"),
    'back': ('q', "Go back to the last view"),
    'exit': ('Q', "Exit the program"),
    'list diff': ('D', "Show the diff of the current version and the"
                  " previous one"),
    'reply': ('r', "Reply to a comment"),
    'like': ('L', "Toggle your 'like' of a comment"),
    'update': ('u', "Update the entire list"),
    'load more': ('m', "Load more objects"),
    'load much more': ('M', "Load much more objects"
                       " (five times the regular amount)"),
    'cli browser': ('b', "Open with CLI browser"),
    'gui browser': ('B', "Open with GUI browser"),
}

if 'KeyMap' in config:
    for k, v in config['KeyMap'].items():
        KEYS[k] = (v, KEYS[k][1])


all_keys = [v[0] for _, v in KEYS.items()]
if not len(all_keys) == len(set(all_keys)):
    log.warning("There are duplicate defined keys!")

KEY_ACTIONS = {v[0]: k for k, v in KEYS.items()}
