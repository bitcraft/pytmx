#!/usr/bin/env python
# encoding: utf-8
# pip install wheel
# python3 setup.py sdist bdist_wheel
# python3 -m twine upload --repository pypi dist/*
from setuptools import setup

setup(
    name="PyTMX",
    version='3.29',
    description='loads tiled tmx maps.  for python 3.3+',
    author='bitcraft',
    author_email='leif.theden@gmail.com',
    packages=['pytmx'],
    license="LGPLv3",
    long_description='https://github.com/bitcraft/PyTMX',
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Games/Entertainment",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries :: pygame",
    ]
)
