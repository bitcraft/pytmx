import logging

__version__ = (3, 20, 0)
__author__ = 'bitcraft'
__author_email__ = 'leif.theden@gmail.com'
__description__ = 'Map util_pygam for TMX Files - Python 2 and 3'

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

from .pytmx import *
import util_pygame

