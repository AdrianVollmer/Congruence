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

import argparse
import xdg
import os
import yaml

parser = argparse.ArgumentParser(
    description="A command line interface for Confluence"
                " (by Adrian Vollmer)"
)

parser.add_argument(
    '-v', '--version', action='version', version='congruence 0.1'
)

parser.add_argument(
    '-l', '--log-level',
    type=int,
    default=None,
    help="enable logging to a file with the given log level (0-4)"
)

args = parser.parse_args()

config_home = os.path.join(xdg.XDG_CONFIG_HOME, "congruence")
config_file = os.path.join(config_home, "config.yaml")
cache_home = os.path.join(xdg.XDG_CACHE_HOME, "congruence")
cookie_jar = os.path.join(cache_home, "cookiejar.dat")

for d in [cache_home, config_home]:
    if not os.path.exists(d):
        os.makedirs(d)

with open(config_file, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

MANDATORY_ARGUMENTS = [
    "Host",
    "Protocol",
    "Username",
    "Password_Command",
]
for m in MANDATORY_ARGUMENTS:
    if m not in config:
        raise IndexError("Mandatory argument not set in config: %s" % m)

# TODO set default values
