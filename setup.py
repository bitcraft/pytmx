#!/usr/bin/env python
#encoding: utf-8

from setuptools import setup
import os
import pytmx

def read(file_name):
    with open(os.path.join(os.path.dirname(__file__), file_name)) as fd:
            return fd.read()

setup(name="PyTMX",
        version=pytmx.__version__,
        description='Map loader for TMX Files',
        author='bitcraft',
        packages=['pytmx',],
        license = "LGPLv3",
        long_description=read('readme.md'),
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
