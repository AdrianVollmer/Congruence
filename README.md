ccli
====

A command line interface to Atlassian Confluence.

Because Confluence at my company loads a whopping 9.13MB of JavaScript just
to see the home page. This program is inspired by mutt and newsboat and has
a minimalist approach to this bloated but quite useful piece of software.

Getting started
---------------

Make sure you have all dependencies installed. The easiest is to just
execute `pip3 install --user -r requirements.txt`. Alternatively, use your
favorite virtual environment manager.

Next, copy `config.yaml.sample` to `$XDG_CONFIG_HOME/ccli/` (or
`$HOME/.config/ccli/` if `$XDG_CONFIG_HOME` is not defined) and edit it to
your liking. At the very least, you have to modify `Host`, `Username` and
`PasswordCommand`.

License
-------

GPLv3. See LICENSE for more information.

Author
------

Adrian Vollmer, 2020
