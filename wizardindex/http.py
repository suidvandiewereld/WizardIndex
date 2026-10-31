import os

import requests

HEADERS = {"User-Agent": "WizardIndex/0.1 (+https://github.com/suidvandiewereld/WizardIndex)"}
TIMEOUT = 60


def get(url: str, **kwargs) -> requests.Response:
    headers = dict(HEADERS)
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    resp = requests.get(url, headers=headers, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp


def text(url: str) -> str:
    resp = get(url)
    resp.encoding = "utf-8"
    return resp.text


def json(url: str):
    return get(url).json()
