#  ccli: A command line interface to Confluence
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
    '-v', '--version', action='version', version='ccli 0.1'
)

parser.add_argument(
    '-d', '--debug',
    default=False,
    action='store_true',
    help="enable debug mode"
)

args = parser.parse_args()

config_home = os.path.join(xdg.XDG_CONFIG_HOME, "ccli")
config_file = os.path.join(config_home, "config.yaml")
cache_home = os.path.join(xdg.XDG_CACHE_HOME, "ccli")
cookie_jar = os.path.join(cache_home, "cookiejar.dat")

for d in [cache_home, config_home]:
    if not os.path.exists(d):
        os.makedirs(d)

with open(config_file, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
