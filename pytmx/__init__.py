"""
Copyright (C) 2012-2021, Leif Theden <leif.theden@gmail.com>

This file is part of pytmx.

pytmx is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

pytmx is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with pytmx.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging

from .pytmx import *

logger = logging.getLogger(__name__)

try:
    from pytmx.util_pygame import load_pygame
except ImportError:
    logger.debug("cannot import pygame tools")

__version__ = (3, 31)
__author__ = "bitcraft"
__author_email__ = "leif.theden@gmail.com"
__description__ = "Map loader for TMX Files - Python 3.3 +"
