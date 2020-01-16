from ccli.args import config
from requests import Session
import time

from bs4 import BeautifulSoup

session = Session()
if "CA" in config:
    session.verify = config["CA"]

HOST = config["Host"]
BASE_URL = f"https://{HOST}"
XSRF = ""


def get_timestamp():
    timestamp = str(int(time.time()*1000))
    return timestamp


def make_request(url, params={}, data=None, method="GET", headers={}):
    url = f"{BASE_URL}/{url}"
    if data or method == "POST":
        headers["X-Atlassian-Token"] = XSRF
        response = session.post(url, params=params, data=data, headers=headers)
    else:
        response = session.get(url, params=params, headers=headers)
    return response


def authenticate_session(user, password):
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
