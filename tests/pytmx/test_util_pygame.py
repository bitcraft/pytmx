import unittest
from unittest.mock import MagicMock, Mock, patch

import pygame
from pygame.rect import Rect
from pygame.surface import Surface

import pytmx
from pytmx.util_pygame import (
    TileFlags,
    build_rects,
    handle_transformation,
    pygame_image_loader,
    simplify,
    smart_convert,
)


class TestPyTMXPygameIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.screen = pygame.display.set_mode((1, 1))

    def test_handle_transformation_no_flags(self):
        tile = Surface((32, 32))
        flags = MagicMock(
            flipped_diagonally=False,
            flipped_horizontally=False,
            flipped_vertically=False,
        )
        transformed_tile = handle_transformation(tile, flags)
        self.assertEqual(transformed_tile, tile)

    def test_handle_transformation_flipped_diagonally(self):
        tile = Surface((32, 32))
        flags = MagicMock(
            flipped_diagonally=True,
            flipped_horizontally=False,
            flipped_vertically=False,
        )
        transformed_tile = handle_transformation(tile, flags)
        self.assertNotEqual(transformed_tile, tile)

    def test_handle_transformation_flipped_horizontally(self):
        tile = Surface((32, 32))
        flags = MagicMock(
            flipped_diagonally=False,
            flipped_horizontally=True,
            flipped_vertically=False,
        )
        transformed_tile = handle_transformation(tile, flags)
        self.assertNotEqual(transformed_tile, tile)

    def test_handle_transformation_flipped_vertically(self):
        tile = Surface((32, 32))
        flags = MagicMock(
            flipped_diagonally=False,
            flipped_horizontally=False,
            flipped_vertically=True,
        )
        transformed_tile = handle_transformation(tile, flags)
        self.assertNotEqual(transformed_tile, tile)

    def test_smart_convert_no_colorkey(self):
        original = Surface((32, 32))
        colorkey = None
        pixelalpha = False
        converted_tile = smart_convert(original, colorkey, pixelalpha)
        self.assertEqual(converted_tile.get_flags() & pygame.SRCALPHA, 0)

    def test_smart_convert_colorkey(self):
        original = Surface((32, 32))
        colorkey = (255, 255, 255)
        pixelalpha = False
        converted_tile = smart_convert(original, colorkey, pixelalpha)
        self.assertEqual(converted_tile.get_flags() & pygame.SRCALPHA, 0)

    def test_smart_convert_pixelalpha(self):
        original = Surface((32, 32), pygame.SRCALPHA)
        colorkey = None
        pixelalpha = True
        converted_tile = smart_convert(original, colorkey, pixelalpha)
        self.assertEqual(converted_tile.get_flags() & pygame.SRCALPHA, pygame.SRCALPHA)

    @patch("pygame.image.load")
    def test_pygame_image_loader(self, mock_load):
        filename = "test_image.png"
        mock_load.return_value = Surface((32, 32))
        load_image_func = pygame_image_loader(filename, None)
        tile = load_image_func()
        self.assertIsInstance(tile, Surface)

    @patch("pygame.image.load")
    def test_pygame_image_loader_rect(self, mock_load):
        filename = "test_image.png"
        mock_load.return_value = Surface((32, 32))
        load_image_func = pygame_image_loader(filename, None)
        rect = pygame.Rect(0, 0, 16, 16)
        tile = load_image_func(rect=rect)
        self.assertIsInstance(tile, Surface)

    @patch("pygame.image.load")
    def test_pygame_image_loader_flags(self, mock_load):
        filename = "test_image.png"
        mock_load.return_value = Surface((32, 32))
        load_image_func = pygame_image_loader(filename, None)
        flags = MagicMock(
            flipped_diagonally=True, flipped_horizontally=True, flipped_vertically=True
        )
        tile = load_image_func(flags=flags)
        self.assertIsInstance(tile, Surface)

    def test_invalid_colorkey_type(self):
        with self.assertRaises(ValueError):
            pygame_image_loader("fake.png", {"not": "valid"})

    @patch("pygame.image.load")
    def test_colorkey_hex_without_hash(self, mock_load):
        mock_load.return_value = Surface((32, 32))
        loader = pygame_image_loader("fake.png", "ff00ff")
        self.assertTrue(callable(loader))

    @patch("pygame.image.load")
    def test_pygame_image_loader_out_of_bounds(self, mock_load):
        mock_load.return_value = Surface((32, 32))
        loader = pygame_image_loader("fake.png", None)
        with self.assertRaises(ValueError):
            loader(pygame.Rect(100, 100, 10, 10))

    @patch("pygame.image.load")
    def test_pygame_image_loader_rect_and_flags(self, mock_load):
        surface = Surface((64, 64))
        surface.fill((255, 255, 255))
        mock_load.return_value = surface
        flags = MagicMock(
            flipped_diagonally=True, flipped_horizontally=True, flipped_vertically=True
        )
        loader = pygame_image_loader("fake.png", None)
        tile = loader(rect=pygame.Rect(0, 0, 32, 32), flags=flags)
        self.assertIsInstance(tile, Surface)

    def test_smart_convert_preserve_alpha_flag(self):
        surface = Surface((32, 32), pygame.SRCALPHA)
        surface.fill((255, 255, 255, 255))
        tile = smart_convert(surface, None, False, preserve_alpha_flag=True)
        self.assertTrue(tile.get_flags() & pygame.SRCALPHA)


class TestSimplify(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(simplify([], 1, 1), [])

    def test_single_point(self):
        points = [(1, 1)]
        expected_rects = [Rect(1, 1, 1, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_adjacent_points(self):
        points = [(1, 1), (2, 1), (1, 2), (2, 2)]
        expected_rects = [Rect(1, 1, 2, 2)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_non_adjacent_points(self):
        points = [(1, 1), (3, 3), (5, 5)]
        expected_rects = [Rect(1, 1, 1, 1), Rect(3, 3, 1, 1), Rect(5, 5, 1, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_rectangles(self):
        points = [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)]
        expected_rects = [Rect(1, 1, 3, 2)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_large_input(self):
        points = [(x, y) for x in range(10) for y in range(10)]
        expected_rects = [Rect(0, 0, 10, 10)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_tile_size(self):
        points = [(1, 1), (2, 1), (1, 2), (2, 2)]
        expected_rects = [Rect(2, 2, 4, 4)]
        self.assertEqual(simplify(points, 2, 2), expected_rects)

    def test_diagonal_points(self):
        points = [(1, 1), (2, 2), (3, 3)]
        expected_rects = [Rect(1, 1, 1, 1), Rect(2, 2, 1, 1), Rect(3, 3, 1, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_vertical_line(self):
        points = [(1, 1), (1, 2), (1, 3), (1, 4)]
        expected_rects = [Rect(1, 1, 1, 4)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_horizontal_line(self):
        points = [(1, 1), (2, 1), (3, 1), (4, 1)]
        expected_rects = [Rect(1, 1, 4, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_l_shape(self):
        points = [(1, 1), (2, 1), (3, 1), (3, 2), (3, 3)]
        expected_rects = [Rect(1, 1, 3, 1), Rect(3, 2, 1, 2)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_t_shape(self):
        points = [(1, 1), (2, 1), (3, 1), (2, 2), (2, 3)]
        expected_rects = [Rect(1, 1, 3, 1), Rect(2, 2, 1, 2)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_cross_shape(self):
        points = [(1, 1), (2, 1), (3, 1), (2, 2), (2, 3), (1, 2), (3, 2)]
        expected_rects = [Rect(1, 1, 3, 2), Rect(2, 3, 1, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_large_l_shape(self):
        points = [
            (1, 1),
            (2, 1),
            (3, 1),
            (4, 1),
            (5, 1),
            (5, 2),
            (5, 3),
            (5, 4),
            (5, 5),
        ]
        expected_rects = [Rect(1, 1, 5, 1), Rect(5, 2, 1, 4)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_large_t_shape(self):
        points = [
            (1, 1),
            (2, 1),
            (3, 1),
            (4, 1),
            (5, 1),
            (3, 2),
            (3, 3),
            (3, 4),
            (3, 5),
        ]
        expected_rects = [Rect(1, 1, 5, 1), Rect(3, 2, 1, 4)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_overlapping_segments(self):
        points = [(1, 1), (2, 1), (2, 2), (3, 2)]
        expected_rects = [Rect(1, 1, 2, 1), Rect(2, 2, 2, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_hollow_rectangle(self):
        points = [
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 2),
            (3, 2),
            (1, 3),
            (2, 3),
            (3, 3),
        ]
        expected_rects = [
            Rect(1, 1, 3, 1),
            Rect(1, 2, 1, 2),
            Rect(2, 3, 2, 1),
            Rect(3, 2, 1, 1),
        ]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_staggered_columns(self):
        points = [(1, 1), (2, 2), (3, 3)]
        expected_rects = [Rect(1, 1, 1, 1), Rect(2, 2, 1, 1), Rect(3, 3, 1, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)

    def test_scaled_large_block(self):
        points = [(x, y) for x in range(5) for y in range(5)]
        expected_rects = [Rect(0, 0, 10, 10)]
        self.assertEqual(simplify(points, 2, 2), expected_rects)

    def test_row_with_gaps(self):
        points = [(1, 1), (2, 1), (4, 1), (5, 1)]
        expected_rects = [Rect(1, 1, 2, 1), Rect(4, 1, 2, 1)]
        self.assertEqual(simplify(points, 1, 1), expected_rects)


class TestBuildRects(unittest.TestCase):

    def setUp(self):
        self.tmxmap = Mock(spec=pytmx.TiledMap)
        self.tmxmap.width = 10
        self.tmxmap.height = 10
        self.tmxmap.tilewidth = 32
        self.tmxmap.tileheight = 32
        self.tmxmap.tilesets = [
            Mock(spec=pytmx.TiledTileset),
            Mock(spec=pytmx.TiledTileset),
        ]
        self.tmxmap.tilesets[0].name = "tileset1"
        self.tmxmap.tilesets[1].name = "tileset2"
        self.tmxmap.layers = [
            Mock(spec=pytmx.TiledTileLayer),
            Mock(spec=pytmx.TiledTileLayer),
        ]
        self.tmxmap.layers[0].name = "layer1"
        self.tmxmap.layers[0].data = [[1 for _ in range(10)] for _ in range(10)]
        self.tmxmap.layers[1].name = "layer2"
        self.tmxmap.layers[1].data = [[1 for _ in range(10)] for _ in range(10)]
        self.tmxmap.get_layer_data = Mock(
            return_value=[[1 for _ in range(10)] for _ in range(10)]
        )
        self.tmxmap.map_gid = Mock(return_value=[(1, 0)])

    def test_build_rects_with_int_layer_and_int_tileset(self):
        result = build_rects(self.tmxmap, 0, 0, 1)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], Rect)

    def test_build_rects_with_str_layer_and_str_tileset(self):
        result = build_rects(self.tmxmap, "layer1", "tileset1", 1)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], Rect)

    def test_build_rects_with_invalid_layer(self):
        with self.assertRaises(ValueError):
            build_rects(self.tmxmap, "invalid_layer", 0, 1)

    def test_build_rects_with_invalid_tileset(self):
        with self.assertRaises(IndexError):
            build_rects(self.tmxmap, 0, 2, 1)

    def test_build_rects_with_invalid_tileset_type(self):
        with self.assertRaises(ValueError):
            build_rects(self.tmxmap, 0, "invalid_type", 1)

    def test_build_rects_with_invalid_gid(self):
        self.tmxmap.map_gid = Mock(return_value=[])
        result = build_rects(self.tmxmap, 0, 0, 1)
        self.assertIsInstance(result, list)

    def test_build_rects_with_no_gid(self):
        result = build_rects(self.tmxmap, 0, 0, None)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], Rect)

    def test_layer_with_no_name(self):
        self.tmxmap.layers[0].name = None
        with self.assertRaises(ValueError):
            build_rects(self.tmxmap, "layer1", 0, 1)

    def test_tileset_with_no_name(self):
        self.tmxmap.tilesets[0].name = None
        with self.assertRaises(ValueError):
            build_rects(self.tmxmap, "layer1", "tileset1", 1)

    def test_gid_not_in_layer_data(self):
        self.tmxmap.map_gid = Mock(return_value=[(999, 0)])
        result = build_rects(self.tmxmap, "layer1", 0, 999)
        self.assertEqual(result, [])

    def test_sparse_tile_distribution(self):
        data = [[0 for _ in range(10)] for _ in range(10)]
        data[1][1] = 1
        data[5][5] = 1
        self.tmxmap.layers[0].data = data
        result = build_rects(self.tmxmap, "layer1", 0, None)
        self.assertTrue(len(result) >= 2)

    def test_build_rects_without_tileset(self):
        result = build_rects(self.tmxmap, "layer1", None, None)
        self.assertIsInstance(result, list)


class TestHandleTransformation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.tile = pygame.Surface((32, 32))
        self.tile.fill((255, 0, 0))

    def test_no_flags(self):
        flags = TileFlags(False, False, False)
        new_tile = handle_transformation(self.tile, flags)
        self.assertEqual(new_tile.get_size(), self.tile.get_size())

    def test_flipped_diagonally(self):
        flags = TileFlags(False, False, True)
        new_tile = handle_transformation(self.tile, flags)
        self.assertEqual(new_tile.get_size(), self.tile.get_size())

    def test_flipped_diagonally_non_square(self):
        non_square_tile = pygame.Surface((32, 64))
        non_square_tile.fill((255, 0, 0))
        flags = TileFlags(False, False, True)
        with self.assertRaises(ValueError):
            handle_transformation(non_square_tile, flags)

    def test_flipped_horizontally(self):
        flags = TileFlags(True, False, False)
        new_tile = handle_transformation(self.tile, flags)
        self.assertEqual(new_tile.get_size(), self.tile.get_size())

    def test_flipped_vertically(self):
        flags = TileFlags(False, True, False)
        new_tile = handle_transformation(self.tile, flags)
        self.assertEqual(new_tile.get_size(), self.tile.get_size())

    def test_flipped_both(self):
        flags = TileFlags(True, True, False)
        new_tile = handle_transformation(self.tile, flags)
        self.assertEqual(new_tile.get_size(), self.tile.get_size())

    def test_flipped_all(self):
        flags = TileFlags(True, True, True)
        new_tile = handle_transformation(self.tile, flags)
        self.assertEqual(new_tile.get_size(), self.tile.get_size())


class TestSmartConvert(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1, 1))  # Needed for convert()
        cls.red = (255, 0, 0, 255)
        cls.transparent = (0, 0, 0, 0)

        cls.base_surface = pygame.Surface((32, 32))
        cls.base_surface.fill(cls.red)

        cls.alpha_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        cls.alpha_surface.fill((255, 0, 0, 128))  # semi-transparent

        cls.edge_transparency_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        cls.edge_transparency_surface.fill((255, 255, 255, 255))
        for x in range(32):
            cls.edge_transparency_surface.set_at((x, 0), cls.transparent)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_no_colorkey(self):
        result = smart_convert(self.base_surface, None, False)
        self.assertEqual(result.get_size(), self.base_surface.get_size())
        self.assertFalse(result.get_flags() & pygame.SRCALPHA)

    def test_pixelalpha_enabled(self):
        result = smart_convert(self.alpha_surface, None, True)
        self.assertTrue(result.get_flags() & pygame.SRCALPHA)

    def test_colorkey_basic(self):
        result = smart_convert(self.base_surface, self.red, False)
        self.assertEqual(result.get_colorkey(), self.red)

    def test_colorkey_rleaccel(self):
        surface = pygame.Surface((32, 32))
        surface.fill(self.red)
        result = smart_convert(surface, self.red, False)
        self.assertEqual(result.get_colorkey(), self.red)
        self.assertIn(result.get_flags() & pygame.RLEACCEL, [0, pygame.RLEACCEL])

    def test_sparse_colorkey(self):
        surface = pygame.Surface((32, 32))
        surface.fill((0, 0, 255))
        surface.set_at((0, 0), self.red)
        result = smart_convert(surface, self.red, False)
        self.assertEqual(result.get_colorkey(), self.red)
        self.assertFalse(result.get_flags() & pygame.RLEACCEL)

    def test_edge_transparency_handling(self):
        result = smart_convert(self.edge_transparency_surface, None, True)
        self.assertTrue(result.get_flags() & pygame.SRCALPHA)

    def test_colorkey_with_pixelalpha_enabled(self):
        result = smart_convert(self.base_surface, self.red, True)
        self.assertEqual(result.get_colorkey(), self.red)

    @patch("pygame.mask.from_surface")
    def test_mask_failure_fallback(self, mock_mask):
        mock_mask.side_effect = Exception("Fake mask failure")
        result = smart_convert(self.base_surface, None, False)
        self.assertTrue(result.get_flags() & pygame.SRCALPHA)

    def test_returned_surface_format(self):
        result = smart_convert(self.base_surface, None, False)
        self.assertFalse(result.get_flags() & pygame.SRCALPHA)

    def test_colorkey_and_pixelalpha_combinations(self):
        test_cases = [
            {"colorkey": None, "pixelalpha": False},
            {"colorkey": None, "pixelalpha": True},
            {"colorkey": self.red, "pixelalpha": False},
            {"colorkey": self.red, "pixelalpha": True},
        ]

        for case in test_cases:
            with self.subTest(case=case):
                result = smart_convert(
                    self.base_surface, case["colorkey"], case["pixelalpha"]
                )
                self.assertEqual(result.get_size(), self.base_surface.get_size())

    def test_conversion_time_large_surface(self):
        import timeit

        large = pygame.Surface((512, 512))
        large.fill(self.red)

        # Wrap smart_convert call in a lambda for timing
        duration = timeit.timeit(lambda: smart_convert(large, None, False), number=10)
        print(f"Conversion time for large surface (512x512): {duration:.4f} seconds")
        self.assertLess(duration, 1.0)  # Arbitrary performance threshold

    def test_batch_tile_conversion(self):
        tiles = [pygame.Surface((32, 32)) for _ in range(50)]
        for tile in tiles:
            tile.fill(self.red)
        results = [smart_convert(tile, self.red, False) for tile in tiles]
        for i, result in enumerate(results):
            self.assertEqual(result.get_size(), tiles[i].get_size())

    def test_gradient_alpha_surface(self):
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        for y in range(32):
            alpha = int(255 * (y / 31))  # vertical gradient
            for x in range(32):
                surface.set_at((x, y), (255, 0, 0, alpha))
        result = smart_convert(surface, None, True)
        self.assertTrue(result.get_flags() & pygame.SRCALPHA)

    def test_colorkey_near_match(self):
        surface = pygame.Surface((32, 32))
        surface.fill((255, 0, 1))  # almost red
        result = smart_convert(surface, (255, 0, 0), False)
        self.assertNotEqual(result.get_colorkey(), (255, 0, 0))  # should not match

    def test_zero_sized_surface(self):
        surface = pygame.Surface((0, 0))
        result = smart_convert(surface, None, False)
        self.assertEqual(result.get_size(), (0, 0))

    def test_preserve_alpha_flag_enabled(self):
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        surface.fill((255, 255, 255, 255))  # fully opaque
        result = smart_convert(surface, None, False, preserve_alpha_flag=True)
        self.assertTrue(result.get_flags() & pygame.SRCALPHA)

    def test_conversion_consistency(self):
        surface = pygame.Surface((32, 32))
        surface.fill((123, 123, 123))
        result1 = smart_convert(surface, None, False)
        result2 = smart_convert(surface, None, False)
        self.assertEqual(result1.get_flags(), result2.get_flags())
