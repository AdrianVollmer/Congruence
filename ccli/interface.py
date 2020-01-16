from ccli.args import config, cookie_jar

import json
from requests import Session, utils
from shlex import split
from subprocess import check_output
import time

from bs4 import BeautifulSoup

session = Session()
if "CA" in config:
    session.verify = config["CA"]
if "Proxy" in config:
    proto, host = config["Proxy"].split("://")
    session.proxies = {"proto": host}


HOST = config["Host"]
PROTO = config["Protocol"]
BASE_URL = f"{PROTO}://{HOST}"
XSRF = ""


def get_timestamp():
    timestamp = str(int(time.time()*1000))
    return timestamp


def make_request(url, params={}, data=None, method="GET", headers={}):
    url = f"{BASE_URL}/{url}"
    attempts = 0
    while attempts < 2:
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
        if response.status_code == 401:
            authenticate_session()
        else:
            break
    return response


def save_session():
    cookies = utils.dict_from_cookiejar(session.cookies)
    cookies["XSRF"] = XSRF
    with open(cookie_jar, 'w') as f:
        json.dump(cookies, f)


def load_session():
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
    user = config["Username"]
    password = check_output(split(config["Password_Command"]))[:-1].decode()

    response = make_request(
        "dologin.action",
        params={
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


load_session()
