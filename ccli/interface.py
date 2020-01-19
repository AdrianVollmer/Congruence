#  ccli: A command line interface to Confluence
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

from ccli.args import config, cookie_jar
from ccli.logging import log

import json
from requests import Session, utils
from shlex import split
from subprocess import check_output
import time

from bs4 import BeautifulSoup
import html2text

session = Session()
if "CA" in config:
    session.verify = config["CA"]
if "Proxy" in config:
    session.proxies = {config["Protocol"]: config["Proxy"]}


HOST = config["Host"]
PROTO = config["Protocol"]
BASE_URL = f"{PROTO}://{HOST}"
XSRF = ""


def get_timestamp():
    timestamp = str(int(time.time()*1000))
    return timestamp


def make_request(url, params={}, data=None, method="GET", headers={}):
    if not url.startswith(BASE_URL):
        url = f"{BASE_URL}/{url}"
    attempts = 0
    while attempts < 2:
        log.info(f"Requesting {url}")
        if data or method == "POST":
            headers["X-Atlassian-Token"] = XSRF
            response = session.post(
                url,
                params=params,
                data=data,
                headers=headers
            )
        else:
            response = session.get(url, params=params, headers=headers)
        attempts += 1
        if not_authenticated(response):
            log.error("Not logged in, authenticating...")
            authenticate_session()
        else:
            break
    return response


def not_authenticated(response):
    if response.status_code == 401:
        return True
    if (
        response.status_code == 404
        and response.headers["content-type"] == "application/json"
    ):
        j = json.loads(response.text)
        if not j['data']['authorized']:
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
    )
    soup = BeautifulSoup(response.text, features="lxml")
    global XSRF
    XSRF = soup.find("meta", {"id": "atlassian-token"})["content"]
    save_session()


def html_to_text(html):
    try:
        return html2text.html2text(html).strip()
    except Exception as e:
        log.exception(e)
        return html


load_session()
