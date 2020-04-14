import unittest

from pytmx import convert_to_bool


class TestConvertToBool(unittest.TestCase):
    def test_string_string_true(self):
        self.assertTrue(convert_to_bool("1"))
        self.assertTrue(convert_to_bool("y"))
        self.assertTrue(convert_to_bool("Y"))
        self.assertTrue(convert_to_bool("t"))
        self.assertTrue(convert_to_bool("T"))
        self.assertTrue(convert_to_bool("yes"))
        self.assertTrue(convert_to_bool("Yes"))
        self.assertTrue(convert_to_bool("YES"))
        self.assertTrue(convert_to_bool("true"))
        self.assertTrue(convert_to_bool("True"))
        self.assertTrue(convert_to_bool("TRUE"))

    def test_string_string_false(self):
        self.assertFalse(convert_to_bool("0"))
        self.assertFalse(convert_to_bool("n"))
        self.assertFalse(convert_to_bool("N"))
        self.assertFalse(convert_to_bool("f"))
        self.assertFalse(convert_to_bool("F"))
        self.assertFalse(convert_to_bool("no"))
        self.assertFalse(convert_to_bool("No"))
        self.assertFalse(convert_to_bool("NO"))
        self.assertFalse(convert_to_bool("false"))
        self.assertFalse(convert_to_bool("False"))
        self.assertFalse(convert_to_bool("FALSE"))

    def test_string_number_true(self):
        self.assertTrue(convert_to_bool(1))
        self.assertTrue(convert_to_bool(1.0))

    def test_string_number_false(self):
        self.assertFalse(convert_to_bool(0))
        self.assertFalse(convert_to_bool(0.0))
        self.assertFalse(convert_to_bool(-1))
        self.assertFalse(convert_to_bool(-1.1))

    def test_string_bool_true(self):
        self.assertTrue(convert_to_bool(True))

    def test_string_bool_false(self):
        self.assertFalse(convert_to_bool(False))

    def test_string_bool_none(self):
        self.assertFalse(convert_to_bool(None))

    def test_string_bool_empty(self):
        self.assertFalse(convert_to_bool(""))

    def test_string_bool_whitespace_only(self):
        self.assertFalse(convert_to_bool(" "))
