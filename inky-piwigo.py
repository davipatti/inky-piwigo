#!/usr/bin/env python3

from __future__ import annotations

import logging
import os
import pickle
import requests
import argparse
import random
from pathlib import Path
from PIL import Image, ImageOps, ImageShow

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

    @property
    def loggedOn(self) -> bool:
        """
        Is a user currently logged on?
        """
        logging.info(f"checking status for {self.username}")
        resp = requests.post(
            f"{self.site}/ws.php?format=json",
            data={
                "method": "pwg.session.getStatus",
            },
            cookies=self.cookies,
        )
        return resp.json()["result"]["username"] == self.username

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

    def download_url(self, url: str) -> str:
        """
        Downloads a URL. Returns the filename saved.
        """
        fname = url.split("/")[-1]
        if not Path("img").exists():
            os.mkdir("img")
        path = Path("img").joinpath(fname)
        if not path.exists():
            resp = requests.get(url, cookies=self.cookies)

            with open(path, "wb") as fobj:
                fobj.write(resp.content)

        return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--tag_name")
    parser.add_argument("--site", required=True)
    parser.add_argument("--size", required=False, choices=IMG_SIZES, default="medium")
    parser.add_argument("--loglevel", default="warning")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview the image instead of showing it on the inky display",
    )
    parser.add_argument(
        "--recent_filter",
        help="Program must be run at least this many times before URL is shown again.",
        default=25,
        type=int,
    )
    args = parser.parse_args()

    if args.recent_filter < 0:
        raise ValueError("--recent_filter must be positive")

    logging.basicConfig(level=args.loglevel.upper())

    session = PiwigoSession(args.username, args.password, args.site)

    if not session.loggedOn:
        session.logOn()

    # all URLs that match the tag
    urls = session.tagUrls(args.tag_name, size=args.size)

    # Check history of URLs that have been shown. Exclude any URLs that have been shown
    # recently.
    try:
        recent_urls = Path("history.txt").read_text().split()[-args.recent_filter :]
    except FileNotFoundError:
        recent_urls = []
    not_recent_urls = set(urls) - set(recent_urls)
    candidate_urls = not_recent_urls if not_recent_urls else urls
    url = random.choice(list(candidate_urls))

    # Keep log of URLs that have been shown
    with open("history.txt", "a") as fp:
        fp.write(f"{url}\n")

    fname = session.download_url(url)

    img = Image.open(fname)
    padded = ImageOps.pad(img, (600, 448))

    if args.preview:
        ImageShow.show(padded)

    else:
        from inky import Inky7Colour

        display = Inky7Colour()
        display.set_image(padded)
        display.show()
