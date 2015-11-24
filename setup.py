#!/usr/bin/env python
#encoding: utf-8
#python setup.py sdist upload -r pypi
from setuptools import setup


setup(name="PyTMX",
      version='3.20.15',
      description='loads tiled tmx maps.  for python 2.7 and 3.3+',
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
          "Programming Language :: Python :: 3.4",
          "Topic :: Games/Entertainment",
          "Topic :: Multimedia :: Graphics",
          "Topic :: Software Development :: Libraries :: pygame",
      ],
)
