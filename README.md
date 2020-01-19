Congruence
==========

A command line interface to Atlassian Confluence.

Because Confluence at my company loads a whopping 9.13MB of JavaScript just
to see the home page. This program is inspired by applications like mutt,
newsboat or tig and takes a minimalist approach to accessing this bloated
but quite useful piece of software.

Fortunately, on the flipside, Confluence behaves nicely when interfacing
with other things. There is an API! And there are lots of JSON objects or
XML documents.

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
