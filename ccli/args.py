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

args = parser.parse_args()

config_file = os.path.join(xdg.XDG_CONFIG_HOME, "ccli", "config.yaml")
cache_home = os.path.join(xdg.XDG_CACHE_HOME, "ccli")


with open(config_file, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
