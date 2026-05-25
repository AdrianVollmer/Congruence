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

from __future__ import annotations

import argparse
import os
import sys

import xdg.BaseDirectory
import yaml

from congruence.__init__ import __version__

parser = argparse.ArgumentParser(
    description="A command line interface for Confluence (by Adrian Vollmer)"
)

parser.add_argument(
    "-v",
    "--version",
    action="version",
    version=f"congruence {__version__}",
)

parser.add_argument(
    "-l",
    "--log",
    default=False,
    action="store_true",
    help="enable logging to a file in $XDG_DATA_HOME/congruence",
)

parser.add_argument(
    "-d",
    "--dump-http",
    type=str,
    default=None,
    help="name of a file in which all HTTP requests and response will be dumped (useful for debugging)",
)

parser.add_argument(
    "-c",
    "--config",
    type=str,
    default="",
    help="specify a configuration file",
)

args = parser.parse_args()

data_home: str = xdg.BaseDirectory.save_data_path("congruence")
config_home: str = xdg.BaseDirectory.save_config_path("congruence")
config_file: str = os.path.join(config_home, "config.yaml")
if args.config:
    config_file = args.config
cache_home: str = xdg.BaseDirectory.save_cache_path("congruence")
cookie_jar: str = os.path.join(cache_home, "cookiejar.dat")

for d in [cache_home, config_home, data_home]:
    if not os.path.exists(d):
        os.makedirs(d)

try:
    with open(config_file) as stream:
        config: dict = yaml.safe_load(stream)
except FileNotFoundError:
    print(f"Config file not found: {config_file}", file=sys.stderr)
    sys.exit(1)
except yaml.YAMLError as exc:
    print(f"Failed to parse config file: {exc}", file=sys.stderr)
    sys.exit(1)

if not isinstance(config, dict):
    print("Config file is empty or malformed.", file=sys.stderr)
    sys.exit(1)

MANDATORY_ARGUMENTS = ["Host", "Protocol"]
for m in MANDATORY_ARGUMENTS:
    if m not in config:
        raise ValueError(f"Mandatory argument not set in config: {m}")

DEFAULTS: dict = {
    "CA": True,
    "DateFormat": "%Y-%m-%d %H:%M",
    "Editor": "vim",
    "CliBrowser": "elinks",
    "GuiBrowser": "firefox",
    "ImageViewer": "feh",
}

for key, value in DEFAULTS.items():
    if key not in config:
        config[key] = value

HOST: str = config["Host"]
PROTO: str = config["Protocol"]
BASE_URL: str = f"{PROTO}://{HOST}"
LOG_FILE: str = os.path.join(data_home, "congruence.log")
