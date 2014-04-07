#!/usr/bin/env python
#encoding: utf-8

import os
from setuptools import setup


def read(file_name):
    with open(os.path.join(os.path.dirname(__file__), file_name)) as fd:
        return fd.read()


version = __import__('pytmx').get_version()

setup(
    name="PyTMX",
    version=version,
    author=pytmx.__author__,
    author_email=pytmx.__author_email__,
    description='Tiled Map Loader for Python',
    license="LGPLv3",
    packages=['pytmx'],
    install_requires=['pygame', 'six'],
    long_description='https://github.com/bitcraft/PyTMX',
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Topic :: Games/Entertainment",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries :: pygame",
    ],
)
