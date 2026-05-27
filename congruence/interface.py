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

import json
import re
import time
from datetime import datetime as dt
from datetime import timedelta
from shlex import split
from subprocess import check_output
from urllib.parse import urlencode

import html2text
import markdown
import pytz
from bs4 import BeautifulSoup
from dateutil.parser import parse as dtparse
from requests import Response, Session
from requests.cookies import cookiejar_from_dict
from requests.utils import dict_from_cookiejar

from congruence.app import app
from congruence.args import BASE_URL, args, config, cookie_jar
from congruence.logging import log

session = Session()
if "CA" in config:
    session.verify = config["CA"]
if "Proxy" in config:
    session.proxies = {config["Protocol"]: config["Proxy"]}

XSRF: str = ""


def get_timestamp() -> str:
    return str(int(time.time() * 1000))


def make_request(
    url: str,
    params: dict | None = None,
    data: str | dict | None = None,
    method: str = "GET",
    headers: dict | None = None,
    no_token: bool = False,
    auth: bool = False,
) -> Response:
    """Perform an HTTP request against the Confluence instance.

    :params: dict of URL parameters
    :data: HTTP request body
    :method: HTTP method
    :headers: additional request headers
    :no_token: skip attaching the XSRF token (some endpoints reject it)
    :auth: True when this request is the authentication call itself
    """
    if params is None:
        params = {}
    if headers is None:
        headers = {}

    if not url.startswith(BASE_URL):
        if url.startswith("/"):
            url = f"{BASE_URL}{url}"
        else:
            url = f"{BASE_URL}/{url}"

    attempts = 0
    response: Response | None = None
    while attempts < 2:
        log.info(f"Requesting {url}")
        app.alert(f"Requesting {url}...", "info")
        if not data and method == "GET":
            response = session.get(url, params=params, headers=headers)
        else:
            if not no_token:
                headers["X-Atlassian-Token"] = XSRF
            response = session.request(method, url, params=params, data=data, headers=headers)
        attempts += 1
        response.encoding = "utf-8"
        if not_authenticated(response):
            log.error("Not logged in? Authenticating...")
            if auth:
                raise PermissionError("Permission denied")
            elif not authenticate_session():
                return response
        else:
            break

    if response is None:
        raise RuntimeError("No response received from server")

    if not response.ok:
        app.alert(f"Received HTTP code {response.status_code}", "error")
        return response
    if args.dump_http:
        dump_http(response, args.dump_http)
    app.reset_status()
    return response


def not_authenticated(response: Response) -> bool:
    if response.status_code in (401, 403):
        return True
    if (
        response.status_code == 404
        and "content-type" in response.headers
        and response.headers["content-type"] == "application/json"
    ):
        j = response.json()
        if not j.get("data", {}).get("authorized", True):
            return True
    if (
        response.history
        and response.history[0].status_code == 302
        and "/login.action" in response.history[0].headers.get("location", "")
    ):
        return True
    return False


def save_session() -> None:
    """Save session cookies to cookie jar."""
    cookies = dict_from_cookiejar(session.cookies)
    cookies["XSRF"] = XSRF
    with open(cookie_jar, "w") as f:
        json.dump(cookies, f)


def load_session() -> None:
    """Load session cookies from cookie jar."""
    try:
        with open(cookie_jar) as f:
            cookies = cookiejar_from_dict(json.load(f))
    except FileNotFoundError:
        return
    global XSRF
    xsrf = cookies["XSRF"]
    del cookies["XSRF"]
    XSRF = xsrf or ""
    session.cookies.update(cookies)


def authenticate_session() -> bool:
    """Retrieve a valid session cookie and XSRF token."""
    user = config["Username"]
    password = check_output(split(config["Password_Command"]))[:-1].decode()

    log.info(f"Authenticating user: {user}")
    response = make_request(
        "dologin.action",
        data={
            "os_username": user,
            "os_password": password,
            "login": "Log in",
            "index.action": "",
        },
        method="POST",
        auth=True,
    )
    reason = response.headers.get("X-Seraph-LoginReason", "")
    if reason != "OK":
        app.alert(f"Error while authenticating: {reason}", "error")
        return False
    soup = BeautifulSoup(response.text, features="lxml")
    token_meta = soup.find("meta", {"id": "atlassian-token"})
    if token_meta is None:
        app.alert("Could not find XSRF token in login response", "error")
        return False
    global XSRF
    XSRF = str(token_meta["content"])
    save_session()
    return True


def dump_http(response: Response, filename: str) -> None:
    with open(filename, "a") as f:
        now = dt.now()
        f.write(f"<<<<<< Request ({now})\n")
        f.write(response.request.method or "")
        f.write(" ")
        f.write(response.request.url or "")
        f.write("\n")
        for k, v in response.request.headers.items():
            f.write(f"{k}: {v}\n")
        if response.request.body:
            body = response.request.body
            f.write("\n\n")
            if isinstance(body, str):
                f.write(body)
            elif isinstance(body, bytes):
                f.write(body.decode("utf-8", errors="replace"))
            else:
                f.write(str(body))
        f.write("\n\n")
        f.write(">>>>>> Response\n")
        for k, v in response.headers.items():
            f.write(f"{k}: {v}\n")
        f.write("\n\n")
        if response.text:
            f.write(response.text)
        f.write("\n\n")


def html_to_text(
    html: str,
    replace_emoticons: bool = False,
    fix_creation_links: bool = False,
) -> str:
    if replace_emoticons:
        html = convert_emoticons(html)
    if fix_creation_links:
        html = remove_creation_links(html)
    try:
        return html2text.html2text(html).strip()
    except Exception as e:
        log.exception(e)
        return html


def remove_creation_links(html: str) -> str:
    soup = BeautifulSoup(html, features="lxml")
    links = soup.findAll("a", "createlink")  # type: ignore[arg-type]
    for link in links:
        link["href"] = re.sub("[0-9]+$", "", link["href"])
    return str(soup)


def convert_emoticons(html: str) -> str:
    """Replace Confluence emoticon images with regular smileys."""
    emoticon_dict: dict[str, str] = {
        "smile": ":)",
        "sad": ":(",
        "cheeky": ":P",
        "laugh": ":D",
        "wink": ";)",
        "thumbs-up": "👍",
        "thumbs-down": "👎",
        "light-on": "💡",
        "warning": "❗",
        "yellow-star": "⭐",
        "tick": "✔️",
        "cross": "❌",
        "information": "ℹ️",  # noqa: RUF001
        "plus": "➕",  # noqa: RUF001
        "minus": "➖",  # noqa: RUF001
        "question": "❓",
        "heart": "❤️️",
        "broken-heart": "💔",
    }
    soup = BeautifulSoup(html, features="lxml")
    emoticons = soup.findAll("img", "emoticon")  # type: ignore[arg-type]
    for emoticon in emoticons:
        for k, v in emoticon_dict.items():
            if f"emoticon-{k}" in emoticon["class"]:
                emoticon.replace_with(v)
    return str(soup)


def md_to_html(text: str, url_encode: str | None = None) -> str:
    result = markdown.markdown(text)
    if url_encode:
        result = urlencode({url_encode: result})
    return result


def convert_date(date: str | int, frmt: str = "default") -> str:
    """Convert the multitude of date formats to a common one."""
    try:
        parsed = dtparse(str(date))
        now = dt.utcnow().replace(tzinfo=pytz.utc)
    except (ValueError, TypeError, OverflowError):
        if isinstance(date, int):
            parsed = dt.fromtimestamp(date / 1000.0)
            now = dt.now()
        else:
            parsed = dt.strptime(date, "%Y-%m-%dT%H:%M:%S%z")
            now = dt.utcnow().replace(tzinfo=pytz.utc)
    diff = now - parsed
    if frmt == "default":
        return parsed.strftime(config["DateFormat"])
    if frmt == "friendly":
        if diff < timedelta(hours=24):
            return parsed.strftime("%H:%M")
        elif diff < timedelta(days=8):
            return parsed.strftime("%a")
        elif diff < timedelta(days=31):
            return parsed.strftime("%b %d")
        else:
            return parsed.strftime("%x")
    if frmt == "timespan":
        total_seconds = int(diff.total_seconds())
        if diff < timedelta(minutes=60):
            return f"{total_seconds // 60} min ago"
        elif diff < timedelta(hours=24):
            return f"{total_seconds // 3600} hours ago"
        elif diff < timedelta(days=31):
            return f"{diff.days} days ago"
        else:
            return f"{diff.days // 365} years ago"
    return parsed.strftime(config["DateFormat"])


load_session()
