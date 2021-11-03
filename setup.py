#!/usr/bin/env python
# encoding: utf-8
# pip install wheel
# python3 setup.py sdist bdist_wheel
# python3 -m twine upload --repository pypi dist/*
from setuptools import setup

setup(
    name="PyTMX",
    version='3.30',
    description='Loads tiled tmx maps',
    author='bitcraft',
    author_email='leif.theden@gmail.com',
    packages=['pytmx'],
    license="LGPLv3",
    long_description='https://github.com/bitcraft/PyTMX',
    python_requires='>=3.7',
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Games/Entertainment",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries :: pygame",
    ]
)
