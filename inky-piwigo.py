#!/usr/bin/env python3

from __future__ import annotations

import os
from requests import get, post
import argparse
import random
import urllib
from pathlib import Path

from PIL import Image
from inky import Inky7Colour


class PiwigoSession:
    def __init__(
        self, username: str, password: str, site="https://davipatti.piwigo.com"
    ) -> None:
        self.site = site
        self.logon_response = post(
            f"{self.site}/ws.php?format=json",
            data={
                "username": username,
                "password": password,
                "method": "pwg.session.login",
            },
        )
        if self.logon_response.status_code != 200:
            raise Exception("couldn't logon")

    def tagUrls(self, tag: str, size: str) -> list[str]:
        """
        URLs of each image matching the tag are accessed via:

            dict["derivatives"]["xsmall"]["url"]

        For each image. Sizes are:
            'square', 'thumb', 'xsmall', 'small', 'medium', 'large', 'xlarge', 'xxlarge',
            '2small'
        """
        response = get(
            f"{self.site}/ws.php?format=json&method=pwg.tags.getImages&tag_name={tag}",
            cookies=self.logon_response.cookies,
        )
        if response.status_code == 200:
            return [
                image["derivatives"][size]["url"]
                for image in response.json()["result"]["images"]
            ]
        else:
            raise Exception("couldn't fetch image urls")


def download_url(url: str) -> str:
    """Returns the filename saved"""
    fname = url.split("/")[-1]
    if not Path("img").exists():
        os.mkdir("img")
    path = Path("img").joinpath(fname)
    if not Path(path).exists():
        urllib.request.urlretrieve(url, path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument(
        "--size",
        required=False,
        choices=[
            "square",
            "thumb",
            "xsmall",
            "small",
            "medium",
            "large",
            "xlarge",
            "xxlarge",
            "2small",
        ],
        default="medium",
    )
    args = parser.parse_args()

    session = PiwigoSession(args.username, args.password)
    urls = session.tagUrls(args.tag, size=args.size)

    fname = download_url(random.choice(urls))

    img = Image.open(fname).resize((600, 400))
    display = Inky7Colour()
    display.set_image(img)
    display.show()
