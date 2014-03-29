#!/usr/bin/env python
#encoding: utf-8

from setuptools import setup
import os
import pytmx

setup(name="PyTMX",
        version=pytmx.__version__,
        description=pytmx.__description__,
        author=pytmx.__author__,
        author_email=pytmx.__author_email__,
        packages=['pytmx',],
        install_requires=['pygame'],
        license = "LGPLv3",
        long_description='https://github.com/bitcraft/PyTMX',
        classifiers=[
            "Intended Audience :: Developers",
            "Development Status :: 4 - Beta",
            "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
            "Programming Language :: Python :: 2.6",
            "Programming Language :: Python :: 2.7",
            "Topic :: Games/Entertainment",
            "Topic :: Multimedia :: Graphics",
            "Topic :: Software Development :: Libraries :: pygame",
        ],
        )
