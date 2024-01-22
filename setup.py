#!/usr/bin/env python
"""Bootstrap the development environment.

This is not a setuptools file. Everything included
in this script must be from the Python standard library
and platform agnostic for the `just` task manager.
"""
from urllib import request

JUST = "https://"

def main() -> None:
    request.urlopen(url=JUST)

if __name__ == "__main__":
    main()
