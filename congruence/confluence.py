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


from congruence.interface import make_request
from congruence.logging import log

import json
import re


def get_nested_content(url, attr_picker):
    """Retrieve content from the Confluence API

    url: the REST endpoint to use.
    attr_picker: a function that takes a dictionary and returns a
        different (e.g. a condensend one) dictionary.
    """
    def get_by_id(children, cid):
        for c in children:
            if cid in list(c.keys()):
                return c

    items = []
    while True:
        r = make_request(url)
        parsed = json.loads(r.text)
        items += parsed["results"]
        links = parsed["_links"]
        if "next" in links:
            url = links["next"]
        else:
            break

    result = []

    # Build the structure returned by Confluence into something more useful.
    # Most importantly, it's a flat list of all items with each item
    # possessing a list of its ancestors. We want a nested list.
    # Also, we only keep track of certain attributes.
    for c in items:
        parent = result
        # Step down the ancestor list
        for a in reversed(c["ancestors"]):
            parent = get_by_id(parent, a["id"])["children"]

        parent.append({
            c["id"]: attr_picker(c),
            "children": [],
        })

    return result


def get_id_from_url(url):
    log.debug("Get pageId of %s" % url)
    m = re.search(r'pageId=([0-9]*)', url)
    if m:
        return m.groups()[0]
    m = re.search(r'display/([^/]+)(.*)/([^/]*)', url.split("?")[0])
    if not m:
        return None
    space, date, title = m.groups()[:3]
    type = "blogpost" if date else "page"
    log.debug(f"Getting id of '{space}/{title}', type '{type}'")
    # Better leave it all URL encoded
    r = make_request("rest/api/content?"
                     + f"type={type}&title={title}&spaceKey={space}")
    j = json.loads(r.text)
    if j["results"]:
        return j["results"][0]["id"]
    return None
