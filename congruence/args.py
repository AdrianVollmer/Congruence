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

from congruence.__init__ import __version__

import congruence.environment as env

import xdg.BaseDirectory
import yaml

import argparse
import os

parser = argparse.ArgumentParser(
    description="A command line interface for Confluence"
                " (by Adrian Vollmer)"
)

parser.add_argument(
    '-v', '--version',
    action='version',
    version='congruence %s' % __version__,
)

parser.add_argument(
    '-l', '--log',
    default=False,
    action='store_true',
    help="enable logging to a file in $XDG_DATA_HOME/congruence"
)

#  parser.add_argument(
#      '-d', '--dump-http',
#      type=str,
#      default=None,
#      help="name of a file in which all HTTP requests and response will"
#           " be dumped (useful for debugging)"
#  )

parser.add_argument(
    '-c', '--config',
    type=str,
    default="",
    help="specify a configuration file"
)

MANDATORY_OPTIONS = [
    "Host",
    "Protocol",
]

DEFAULT_OPTIONS = {
    "CA": True,  # will use the system's cert store
    "DateFormat": "%Y-%m-%d %H:%M",
    "Editor": "vim",
    "CliBrowser": "elinks",
    "GuiBrowser": "firefox",
    "ImageViewer": "feh",
}


def load_config(args=None):
    data_home = xdg.BaseDirectory.save_data_path("congruence")
    config_home = xdg.BaseDirectory.save_config_path("congruence")
    cache_home = xdg.BaseDirectory.save_cache_path("congruence")
    config_file = os.path.join(config_home, "config.yaml")

    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)
    if args.config:
        config_file = args.config

    for d in [cache_home, config_home, data_home]:
        if not os.path.exists(d):
            os.makedirs(d)

    with open(config_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    for m in MANDATORY_OPTIONS:
        if m not in config:
            raise IndexError("Mandatory options not set in config: %s" % m)

    for key, value in DEFAULT_OPTIONS.items():
        if key not in config:
            config[key] = value

    # Store everything in config
    HOST = config["Host"]
    PROTO = config["Protocol"]
    config['BaseURL'] = f"{PROTO}://{HOST}"
    if args.log:
        config['LogFile'] = os.path.join(data_home, "congruence.log")
    config['CookieJar'] = os.path.join(cache_home, "cookiejar.dat")

    env.config = config
