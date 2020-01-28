Congruence
==========

A command line interface to Atlassian Confluence.

Because Confluence at my company loads a whopping 9.13MB of JavaScript just
to display the home page.

About
-----

This program is inspired by applications like mutt, newsboat or tig and
takes a minimalist approach to accessing this bloated but quite useful piece
of software.

Fortunately, on the flip side, Confluence behaves nicely when interfacing
with other things. There is an API! With documentation! And there are lots
of JSON objects or XML documents suitable for programmatic processing.

I'm a big believer in minimalism and CLI/TUI tools. They always respond
virtually instantly to user input (safe for communication over the network)
and their keyboard-driven nature makes it a breeze to work with once you
have the keyboard mappings down. Plus, their true power often comes through
their ability to interact with other programs and scripts, which makes
automation so much easier. Displaying Confluence pages in a TUI browser like
elinks or lynx naturally removes all distractions and focuses and what's
most important: the content. Besides pages with lots of images or tables,
this makes it surprisingly pleasant to read. And your fully-fledged GUI
browser is just one key press away...

Naturally, Congruence was written entirely in vim.

Disclaimer: I am not affiliated with Atlassian in any way. At the point of
writing, I only have one Confluence instance to work with. I also never
installed a Confluence and I have only a vague idea of what is a plugin and
what is core functionality. I'm just a regular power user. Tested on
Confluence 6.15.9.

Getting started
---------------

Make sure you have all dependencies installed. The easiest is to just
execute `pip3 install --user -r requirements.txt`. Alternatively, use your
favorite virtual environment manager.

Next, copy `config.yaml.sample` to `$XDG_CONFIG_HOME/congruence/config.yaml` (or
`$HOME/.config/congruence/` if `$XDG_CONFIG_HOME` is not defined) and edit it to
your liking.

License
-------

GPLv3. See LICENSE for more information.

Author
------

Adrian Vollmer, 2020
