import unittest

import croco


class TestEval(unittest.TestCase):
    def test_const(self):
        tests = {
            "1": 1,
            "1.0": 1.0,
            "True": True,
            "False": False,
            "None": None,
            "1 + 2": 3,
            "1 + 2 * 3": 7,
            "2*3 + 1": 7,
            "2*(3 + 1)": 8,
            "2**3": 8,
            "5//2": 2,
            "5%2": 1,
            "'abc'": "abc",
            '"abc"': "abc",
        }

        for code, expected in tests.items():
            with self.subTest(code=code):
                print(">>> ", code)
                self.assertEqual(croco.run(code, mode="eval"), expected)
