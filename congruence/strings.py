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

"""This file contains only user-visible strings"""


REPLY_MSG = """

## Lines starting with a double pound sign will be ignored.
## You can write markdown. Save only whitespace to abort.
## This is the comment you are replying to:
##
"""

DIFF_EMPTY = (
    "It's not clear what changed based on what "
    "Confluence gives us, sorry."
)

PAGE_VIEW_HELP = (
    "What you see here is meta info of a page object."
)

COMMENT_DETAILS_VIEW_HELP = (
    "What you see here is all properties of a comment object."
)

COMMENT_VIEW_HELP = (
    "What you see here are meta info and the content of a comment object."
)

DIFF_VIEW_HELP = (
    "The diff view shows you what changed between to versions."
)

COMMENT_CONTEXT_VIEW_HELP = (
    "This view shows a tree structure of all comments of a page or blog"
    " post."
)
