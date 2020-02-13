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
with other things. There is an API! Check it out:

[![asciicast](https://asciinema.org/a/vEGpJpHqyX3S4wMNCbkuJCLRx.svg)](https://asciinema.org/a/vEGpJpHqyX3S4wMNCbkuJCLRx)

(This is from a public Confluence. If you see yourself in this asciicast and
don't like it, contact me.)

I'm a big believer in minimalism and CLI/TUI tools. They always respond
virtually instantly to user input (safe for communication over the network)
and their keyboard-driven nature makes it a breeze to work with once you
have the keyboard mappings down. Plus, their true power often comes through
their ability to interact with other programs and scripts, which makes
automation so much easier. Displaying Confluence pages in a TUI browser like
elinks or lynx naturally removes all distractions and focuses on what's
most important: the content. Besides pages with lots of images or tables,
this makes it surprisingly pleasant to read. And your fully fledged GUI
browser is just one key press away...

Naturally, Congruence was written entirely in vim.

The goal is primarily to consume content served by Confluence and have
minimal interactions, such as liking content and posting comments. Editing
pages is out of scope for sure.

Disclaimer: I am not affiliated with Atlassian in any way. At the point of
writing, I only have one Confluence instance to work with. I also never
installed a Confluence and I have only a vague idea of what is a plugin and
what is core functionality. I'm just a regular power user. This will work
only with Confluence 6.0 or higher.

Getting started
---------------

Make sure you have all dependencies installed, most importantly Python 3.6
or higher. The easiest is to just execute `pip3 install .`, which will put
an executable named `congruence` in your `~/.local/bin` directory, which
must be in your `$PATH`. Alternatively, use your favorite virtual
environment manager.

Next, copy `config.yaml.sample` to `$XDG_CONFIG_HOME/congruence/config.yaml` (or
`$HOME/.config/congruence/` if `$XDG_CONFIG_HOME` is not defined) and edit it to
your liking.

When using the app, you can always press '?' to see what's going on and what
your next options are.

Ideas for the next release
--------------------------

* Cache metadata
* Keep track of 'seen'/'unseen' objects
* New plugin: interactive search
* Extract links and images of content
* Global blacklist of users for filtering
* Show scroll  percentage in title bar
* Improve search
* Add a 'versions' view and allow diffs between arbitrary versions
* Edit comments

License
-------

GPLv3. See LICENSE for more information.

Author
------

Adrian Vollmer, 2020
