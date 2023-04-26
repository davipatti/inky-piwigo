#!/usr/bin/env python3

from __future__ import annotations

import logging
import os
import pickle
import requests
import argparse
import random
import urllib
import PIL as pil
from pathlib import Path

IMG_SIZES = (
    "square",
    "thumb",
    "xsmall",
    "small",
    "medium",
    "large",
    "xlarge",
    "xxlarge",
    "2small",
)


class PiwigoSession:
    def __init__(self, username: str, password: str, site: str) -> None:
        """
        Start a Piwigo session

        Args:
            username:
            password:
            site: E.g. "https://mysite.piwigo.com"
        """
        self.site = site
        self.username = username
        self.password = password

    def logOn(self) -> None:
        """
        Logs on and saves session cookie to disk.
        """
        logging.info("logging on")

        self.logon_response = requests.post(
            f"{self.site}/ws.php?format=json",
            data={
                "username": self.username,
                "password": self.password,
                "method": "pwg.session.login",
            },
        )

        if self.logon_response.status_code != 200:
            raise Exception("couldn't logon")

        else:
            logging.info("writing cookie")
            with open("pwg_cookie", "wb") as fp:
                pickle.dump(self.logon_response.cookies, fp)

    @property
    def cookies(self) -> requests.cookies.RequestsCookieJar:
        if not Path("pwg_cookie").exists():
            self.logOn()

        with open("pwg_cookie", "rb") as fp:
            logging.info("reading cookie")
            return pickle.load(fp)

    def tagUrls(self, tag_name: str, size: str) -> list[str]:
        """
        URLs of each image with tag_name.

        Sizes are:
            square, thumb, xsmall, small, medium, large, xlarge, xxlarge, 2small
        """
        logging.info(f"fetching urls for tag: {tag_name}")

        response = requests.get(
            f"{self.site}/ws.php?format=json&method=pwg.tags.getImages&tag_name={tag_name}",
            cookies=self.cookies,
        )

        if response.status_code == 200:
            return [
                image["derivatives"][size]["url"]
                for image in response.json()["result"]["images"]
            ]

        else:
            raise Exception("couldn't fetch image urls")


def download_url(url: str) -> str:
    """Downloads a URL and returns the filename saved"""
    fname = url.split("/")[-1]
    if not Path("img").exists():
        os.mkdir("img")
    path = Path("img").joinpath(fname)
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--tag_name", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--size", required=False, choices=IMG_SIZES, default="medium")
    parser.add_argument("--loglevel", default="warning")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview the image instead of showing it on the inky display",
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel.upper())

    session = PiwigoSession(args.username, args.password, args.site)
    urls = session.tagUrls(args.tag_name, size=args.size)

    fname = download_url(random.choice(urls))

    img = pil.Image.open(fname)
    padded = pil.ImageOps.pad(img, (600, 448))

    if args.preview:
        pil.ImageShow.show(padded)

    else:
        from inky import Inky7Colour

        display = Inky7Colour()
        display.set_image(padded)
        display.show()
