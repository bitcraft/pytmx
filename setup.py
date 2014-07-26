#!/usr/bin/env python
#encoding: utf-8

from setuptools import setup


setup(name="PyTMX",
      version='3.19.0',
      description='loads tiles tmx maps.  for python 2.7 and 3.3',
      author='bitcraft',
      author_email='leif.theden@gmail.com',
      packages=['pytmx'],
      install_requires=['six'],
      license="LGPLv3",
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
