"""
some tests for pytmx

WIP
"""

from unittest import TestCase
from logging import getLogger

import pytmx


class TiledMapTest(TestCase):
    filename = 'tests/test01.tmx'

    def setUp(self):
        self.m = pytmx.TiledMap(self.filename)

    def test_load(self):
        pass

    def test_get_tile_image(self):
        image = self.m.get_tile_image(0, 0, 0)

    def test_get_tile_image_by_gid(self):
        # 0 should always return None
        image = self.m.get_tile_image_by_gid(0)
        self.assertIsNone(image)

        image = self.m.get_tile_image_by_gid(1)
        self.assertIsNotNone(image)

    def test_import_pytmx_doesnt_import_pygame(self):
        import pytmx
        import sys
        self.assertTrue('pygame' not in sys.modules)

