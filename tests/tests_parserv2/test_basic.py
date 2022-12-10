import unittest

from parser_v2.struct import Str, Any
from parser_v2.token import Indexer

class TestBasic(unittest.TestCase):
    def test_str(self):
        struct = Str("abc")
        for code in (" abc", "ab", ""):
            self.assertEqual(struct.parse({}, Indexer(code), code), (None, 0))
        for code in ("abc", "abcde"):
            self.assertEqual(struct.parse({}, Indexer(code), code), ("abc", 3))

    def test_any(self):
        struct = Any("abc", "def")
        for code in (" abc", "ab", "deabc"):
            self.assertEqual(struct.parse({}, Indexer(code), code), (None, 0))
        for code in ("abc", "def", "abcde", "defgh"):
            self.assertEqual(struct.parse({}, Indexer(code), code), (code[:3], 3))
