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

from congruence.args import config, cookie_jar, BASE_URL, args
from congruence.logging import log
from congruence.app import app

from urllib.parse import urlencode
from datetime import datetime as dt, timedelta
import json
from requests import Session, utils
from shlex import split
from subprocess import check_output
import time

from bs4 import BeautifulSoup
import html2text
from dateutil.parser import parse as dtparse
import pytz
import markdown


session = Session()
if "CA" in config:
    session.verify = config["CA"]
if "Proxy" in config:
    session.proxies = {config["Protocol"]: config["Proxy"]}


XSRF = ""


def get_timestamp():
    timestamp = str(int(time.time()*1000))
    return timestamp


def make_request(url, params={}, data=None, method="GET", headers={},
                 no_token=False, auth=False):
    """This function performs the actual HTTP request

    :params: dict of URL parameters passed to requests
    :data: string which contains the HTTP body
    :method: HTTP method to use
    :headers: dict of headers passed to requests
    :no_token: set this to True if you need no XSRF token
    :auth: set this to True if this is to authenticate; this will prevent an
        infinite loop
    """

    if not url.startswith(BASE_URL):
        if url.startswith('/'):
            url = f"{BASE_URL}{url}"
        else:
            url = f"{BASE_URL}/{url}"
    attempts = 0
    while attempts < 2:
        log.info(f"Requesting {url}")
        app.alert(f"Requesting {url}...", 'info')
        if not data and method == "GET":
            response = session.get(url, params=params, headers=headers)
        else:
            if not no_token:
                # For whatever reason, some requests fail with a proper XSRF
                # Token... for example posting a comment
                headers["X-Atlassian-Token"] = XSRF
            response = session.request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
            )
        attempts += 1
        response.encoding = 'utf-8'
        if not_authenticated(response):
            log.error("Not logged in? Authenticating...")
            if auth:
                raise PermissionError("Permission denied")
            elif not authenticate_session():
                return response
        else:
            break
    if not response.ok:
        app.alert("Received HTTP code %d" % response.status_code, 'error')
    if args.dump_http:
        dump_http(response, args.dump_http)
    app.reset_status()
    return response


def not_authenticated(response):
    if response.status_code in [401, 403]:
        return True
    if (
        response.status_code == 404
        and "content-type" in response.headers
        and response.headers["content-type"] == "application/json"
    ):
        j = response.json()
        if not j['data']['authorized']:
            return True
    if (
        response.history
        and response.history[0].status_code == 302
        and "/login.action" in response.history[0].headers["location"]
    ):
        return True
    return False


def save_session():
    """Save session cookies to cookie jar"""
    cookies = utils.dict_from_cookiejar(session.cookies)
    cookies["XSRF"] = XSRF
    with open(cookie_jar, 'w') as f:
        json.dump(cookies, f)


def load_session():
    """Load session cookies from cookie jar"""
    try:
        with open(cookie_jar, 'r') as f:
            cookies = utils.cookiejar_from_dict(json.load(f))
    except FileNotFoundError:
        return None
    global XSRF
    XSRF = cookies["XSRF"]
    del cookies["XSRF"]
    session.cookies.update(cookies)


def authenticate_session():
    """Retrieve a valid session cookie and XSRF token"""

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
        auth=True
    )
    reason = response.headers['X-Seraph-LoginReason']
    if not reason == "OK":
        app.alert("Error while autenticating: %s" % reason, "error")
        return False
    soup = BeautifulSoup(response.text, features="lxml")
    global XSRF
    XSRF = soup.find("meta", {"id": "atlassian-token"})["content"]
    save_session()
    return True


def dump_http(response, filename):
    with open(filename, 'a') as f:
        now = dt.now()
        f.write("<<<<<< Request (%s)\n" % now)
        f.write(response.request.method)
        f.write(' ')
        f.write(response.request.url)
        f.write('\n')
        for k, v in response.request.headers.items():
            f.write(f"{k}: {v}\n")
        if response.request.body:
            f.write('\n')
            f.write('\n')
            f.write(response.request.body)
        f.write('\n')
        f.write('\n')
        f.write(">>>>>> Response\n")
        for k, v in response.headers.items():
            f.write(f"{k}: {v}\n")
        f.write('\n')
        f.write('\n')
        if response.text:
            f.write(response.text)
        f.write('\n')
        f.write('\n')


def html_to_text(html):
    try:
        return html2text.html2text(html).strip()
    except Exception as e:
        log.exception(e)
        return html


def md_to_html(text, url_encode=None):
    result = markdown.markdown(text)
    if url_encode:
        result = urlencode({url_encode: result})
    return result


def convert_date(date, frmt='default'):
    """Convert the multitude of date formats to a common one"""
    try:
        date = dtparse(date)
        now = dt.utcnow().replace(tzinfo=pytz.UTC)
    except (ValueError, TypeError):
        if isinstance(date, int):
            date = dt.fromtimestamp(date/1000.)
            now = dt.now()
        else:
            date = dt.strptime(date, "%Y-%m-%dT%H:%M:%S%z")
            now = dt.utcnow().replace(tzinfo=pytz.UTC)
    diff = now - date
    if frmt == 'default':
        return date.strftime(config["DateFormat"])
    if frmt == 'friendly':
        if diff < timedelta(hours=24):
            return date.strftime("%H:%M")
        elif diff < timedelta(days=8):
            return date.strftime("%a")
        elif diff < timedelta(days=31):
            return date.strftime("%b %d")
        else:
            return date.strftime("%x")
    if frmt == 'timespan':
        if diff < timedelta(minutes=60):
            result = diff.minutes
            return "%d min ago" % result
        elif diff < timedelta(hours=24):
            result = diff.hours
            return "%d hours ago" % result
        elif diff < timedelta(days=31):
            result = diff.days
            return "%d days ago" % result
        else:
            result = diff.years
            return "%d years ago" % result


load_session()
