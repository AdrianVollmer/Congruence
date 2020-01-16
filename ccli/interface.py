from requests import Session
import time


session = Session()
session.verify = False

HOST = "confluence.syss.intern"
BASE_URL = f"https://{HOST}"


def get_timestamp():
    timestamp = str(int(time.time()*1000))
    return timestamp


def make_request(url, params={}, method="GET"):
    url = f"{BASE_URL}/{url}"
    if method == "GET":
        response = session.get(url, params=params)
    elif method == "POST":
        response = session.post(url, params=params)
    else:
        # TODO exception
        print("Invalid method: ", method)
        return response
    return response


def authenticate_session(user, password):
    make_request(
        "dologin.action",
        params={
            "os_username": user,
            "os_password": password,
            "login": "Log in",
            "index.action": "",
        },
        method="POST",
    )
