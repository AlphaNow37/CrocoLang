import unittest
from textwrap import dedent

import croco


class TestEval(unittest.TestCase):
    def assert_list(self, tests):
        for code, expected in tests.items():
            with self.subTest(code=code):
                print(">>> ", code)
                self.assertEqual(croco.run(code, mode="eval"), expected)

    def test_const(self):
        tests = {
            "1": 1,
            "1.0": 1.0,
            "True": True,
            "False": False,
            "None": None,
            "1 + 2": 3,
            "1 + 2 * 3": 7,
            "2 *3 + 1": 7,
            "2*(3 + 1)": 8,
            "2**3": 8,
            "5//2": 2,
            "5%2": 1,
            "'abc'": "abc",
            '"abc"': "abc",
        }

        self.assert_list(tests)

    def test_var(self):
        tests = {
            "a = 1": None,
            "a = 1; a": 1,
            "a=    1\na": 1,
            "sfsd5=45+3\nsfsd5": 48,
            "a=1\na+=1\na+1": 3,
            "a=1;b=2;a+b": 3,
            "5 #comment": 5,
            "a=1\na+=1\na+1 #comment": 3,
            "(1\n+1\n\t+1)": 3,
            "1+\\\n1": 2,
        }
        self.assert_list(tests)

    def test_blocks(self):
        tests = dedent("""
        a=1
        if a:
            a=2
        a
        >>> 2
        
        a=0  # Comment
        if a:
            a=2
        else:
            a=3
        # # # comment
        a
        >>> 3
        
        for a in range(3):
            if a==1:
                break
        a
        >>> 1
        
        for a in range(3):
            if a==1:
                continue
        else:
            a=18
        a
        >>> 18
        
        a=0
        while a<3:
            a+=1
        a
        >>> 3
""".strip("\n"))
        for test in tests.split("\n\n"):
            code, expected = test.split("\n>>> ")
            with self.subTest(code=code):
                print(">>> ", code)
                self.assertEqual(str(croco.run(code, mode="eval")), expected)

    def test_long_code(self):
        code = dedent("""
        l = list()
        for i in range(100):
            l.append(i)
        searched = 12
        left = len(l)
        right = len(l)- 1
        while left < right:
            half = (left + right) // 2
            if l[half] < searched:
                left = half + 1
            elif l[half] == searched:
                print("Found", half)
                break
            else:
                right = half - 1
        else:
            print("Not found")
        """)
        croco.run(code, mode="eval")
