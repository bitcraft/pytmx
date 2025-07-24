import base64
import gzip
import struct
import unittest
import zlib

from pytmx import TiledMap, TileFlags, decode_gid, unpack_gids

# Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29
GID_MASK = GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT


class TestDecodeGid(unittest.TestCase):
    def test_no_flags(self):
        raw_gid = 100
        expected_gid, expected_flags = 100, TileFlags(False, False, False)
        self.assertEqual(decode_gid(raw_gid), (expected_gid, expected_flags))

    def test_individual_flags(self):
        # Test for each flag individually
        test_cases = [
            (GID_TRANS_FLIPX + 1, 1, TileFlags(True, False, False)),
            (GID_TRANS_FLIPY + 1, 1, TileFlags(False, True, False)),
            (GID_TRANS_ROT + 1, 1, TileFlags(False, False, True)),
        ]
        for raw_gid, expected_gid, expected_flags in test_cases:
            self.assertEqual(decode_gid(raw_gid), (expected_gid, expected_flags))

    def test_combinations_of_flags(self):
        # Test combinations of flags
        test_cases = [
            (GID_TRANS_FLIPX + GID_TRANS_FLIPY + 1, 1, TileFlags(True, True, False)),
            (GID_TRANS_FLIPX + GID_TRANS_ROT + 1, 1, TileFlags(True, False, True)),
            (GID_TRANS_FLIPY + GID_TRANS_ROT + 1, 1, TileFlags(False, True, True)),
            (
                GID_TRANS_FLIPX + GID_TRANS_FLIPY + GID_TRANS_ROT + 1,
                1,
                TileFlags(True, True, True),
            ),
        ]
        for raw_gid, expected_gid, expected_flags in test_cases:
            self.assertEqual(decode_gid(raw_gid), (expected_gid, expected_flags))

    def test_edge_cases(self):
        # Maximum GID
        max_gid = 2**29 - 1
        self.assertEqual(
            decode_gid(max_gid), (max_gid & ~GID_MASK, TileFlags(False, False, False))
        )

        # Minimum GID
        min_gid = 0
        self.assertEqual(decode_gid(min_gid), (min_gid, TileFlags(False, False, False)))

        # GID with all flags set
        gid_all_flags = GID_TRANS_FLIPX + GID_TRANS_FLIPY + GID_TRANS_ROT + 1
        self.assertEqual(decode_gid(gid_all_flags), (1, TileFlags(True, True, True)))

        # GID with flags in different orders
        test_cases = [
            (GID_TRANS_FLIPX + GID_TRANS_FLIPY + 1, 1, TileFlags(True, True, False)),
            (GID_TRANS_FLIPY + GID_TRANS_FLIPX + 1, 1, TileFlags(True, True, False)),
            (GID_TRANS_FLIPX + GID_TRANS_ROT + 1, 1, TileFlags(True, False, True)),
            (GID_TRANS_ROT + GID_TRANS_FLIPX + 1, 1, TileFlags(True, False, True)),
        ]
        for raw_gid, expected_gid, expected_flags in test_cases:
            self.assertEqual(decode_gid(raw_gid), (expected_gid, expected_flags))

    def test_flag_cache_identity(self):
        raw_gid = GID_TRANS_FLIPX + GID_TRANS_ROT + 1
        _, flags1 = decode_gid(raw_gid)
        _, flags2 = decode_gid(raw_gid)
        self.assertIs(flags1, flags2)

    def test_flag_cache_separation(self):
        gid1 = GID_TRANS_FLIPX + 1
        gid2 = GID_TRANS_FLIPY + 1
        _, f1 = decode_gid(gid1)
        _, f2 = decode_gid(gid2)
        self.assertNotEqual(f1, f2)


class TestRegisterGid(unittest.TestCase):
    def setUp(self):
        self.tmx_map = TiledMap()

    def test_register_gid_with_valid_tiled_gid(self):
        gid = self.tmx_map.register_gid(123)
        self.assertIsNotNone(gid)

    def test_register_gid_with_flags(self):
        flags = TileFlags(1, 0, 1)
        gid = self.tmx_map.register_gid(456, flags)
        self.assertIsNotNone(gid)

    def test_register_gid_zero(self):
        gid = self.tmx_map.register_gid(0)
        self.assertEqual(gid, 0)

    def test_register_gid_max_gid(self):
        max_gid = self.tmx_map.maxgid
        self.tmx_map.register_gid(max_gid)
        self.assertEqual(self.tmx_map.maxgid, max_gid + 1)

    def test_register_gid_duplicate_gid(self):
        gid1 = self.tmx_map.register_gid(123)
        gid2 = self.tmx_map.register_gid(123)
        self.assertEqual(gid1, gid2)

    def test_register_gid_duplicate_gid_different_flags(self):
        gid1 = self.tmx_map.register_gid(123, TileFlags(1, 0, 0))
        gid2 = self.tmx_map.register_gid(123, TileFlags(0, 1, 0))
        self.assertNotEqual(gid1, gid2)

    def test_register_gid_empty_flags(self):
        gid = self.tmx_map.register_gid(123, TileFlags(0, 0, 0))
        self.assertIsNotNone(gid)

    def test_register_gid_all_flags_set(self):
        gid = self.tmx_map.register_gid(123, TileFlags(1, 1, 1))
        self.assertIsNotNone(gid)

    def test_register_gid_repeated_registration(self):
        gid1 = self.tmx_map.register_gid(123)
        gid2 = self.tmx_map.register_gid(123)
        self.assertEqual(gid1, gid2)

    def test_register_gid_flag_equivalence(self):
        gid1 = self.tmx_map.register_gid(42, TileFlags(True, False, False))
        gid2 = self.tmx_map.register_gid(42, TileFlags(1, 0, 0))
        self.assertEqual(gid1, gid2)

    def test_gid_mapping_growth(self):
        initial_max = self.tmx_map.maxgid
        for i in range(5):
            self.tmx_map.register_gid(100 + i)
        self.assertEqual(self.tmx_map.maxgid, initial_max + 5)


class TestUnpackGids(unittest.TestCase):
    def test_base64_no_compression(self):
        gids = [123, 456, 789]
        data = struct.pack("<LLL", *gids)
        text = base64.b64encode(data).decode("utf-8")
        result = unpack_gids(text, encoding="base64")
        self.assertEqual(result, gids)

    def test_base64_gzip_compression(self):
        gids = [123, 456, 789]
        data = struct.pack("<LLL", *gids)
        compressed_data = gzip.compress(data)
        text = base64.b64encode(compressed_data).decode("utf-8")
        result = unpack_gids(text, encoding="base64", compression="gzip")
        self.assertEqual(result, gids)

    def test_base64_zlib_compression(self):
        gids = [123, 456, 789]
        data = struct.pack("<LLL", *gids)
        compressed_data = zlib.compress(data)
        text = base64.b64encode(compressed_data).decode("utf-8")
        result = unpack_gids(text, encoding="base64", compression="zlib")
        self.assertEqual(result, gids)

    def test_base64_unsupported_compression(self):
        text = "some_base64_data"
        with self.assertRaises(ValueError):
            unpack_gids(text, encoding="base64", compression="unsupported")

    def test_csv(self):
        gids = [123, 456, 789]
        text = ",".join(map(str, gids))
        result = unpack_gids(text, encoding="csv")
        self.assertEqual(result, gids)

    def test_unsupported_encoding(self):
        text = "some_data"
        with self.assertRaises(ValueError):
            unpack_gids(text, encoding="unsupported")

    def test_base64_invalid_data(self):
        text = "!!not_base64!!"
        with self.assertRaises(Exception):
            unpack_gids(text, encoding="base64")

    def test_unpack_empty_input(self):
        result = unpack_gids("", encoding="csv")
        self.assertEqual(result, [])

    def test_base64_corrupted_data(self):
        corrupted_text = "not_base64!!%%"
        with self.assertRaises(Exception):
            unpack_gids(corrupted_text, encoding="base64")

    def test_csv_malformed_data(self):
        bad_csv = "12,,hello,34"
        with self.assertRaises(ValueError):
            unpack_gids(bad_csv, encoding="csv")

    def test_base64_truncated_gzip(self):
        gids = [1, 2, 3, 4]
        data = struct.pack("<LLLL", *gids)
        compressed = gzip.compress(data)
        corrupted = compressed[:10]  # chop it
        text = base64.b64encode(corrupted).decode("utf-8")
        with self.assertRaises(Exception):
            unpack_gids(text, encoding="base64", compression="gzip")

    def test_base64_empty_gzip(self):
        compressed = gzip.compress(b"")
        text = base64.b64encode(compressed).decode("utf-8")
        result = unpack_gids(text, encoding="base64", compression="gzip")
        self.assertEqual(result, [])

    def test_base64_wrong_size(self):
        data = b"\x01\x02\x03"  # only 3 bytes
        text = base64.b64encode(data).decode("utf-8")
        with self.assertRaises(struct.error):
            unpack_gids(text, encoding="base64")

    def test_roundtrip_gid_flags(self):
        raw_gid = GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT | 42
        gid, flags = decode_gid(raw_gid)
        reconstructed = gid | (
            (GID_TRANS_FLIPX if flags.flipped_horizontally else 0)
            | (GID_TRANS_FLIPY if flags.flipped_vertically else 0)
            | (GID_TRANS_ROT if flags.flipped_diagonally else 0)
        )
        self.assertEqual(raw_gid, reconstructed)
