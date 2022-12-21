import unittest

from parser_v2 import *


class TestParser(unittest.TestCase):
    def test_basic(self):
        class A(Parser, start="a"):
            a = Any("abc", "def")

        self.assertEqual(A("abc"), "abc")
        self.assertEqual(A("def"), "def")
        self.assertEqual(parse(A, "abc"), "abc")
        try:
            A("ghi")
        except SyntaxError:
            pass
        else:
            self.fail("SyntaxError not raised")

    def test_expected(self):
        class A(Parser, start="a"):
            a = Any("abc", "def").expect("Expected abc or def")

        self.assertEqual(A("abc"), "abc")
        self.assertEqual(A("def"), "def")
        try:
            A("ghi")
        except SyntaxError as e:
            self.assertTrue(str(e).startswith("Expected abc or def"))
        else:
            self.fail("SyntaxError not raised")

    def test_json(self):
        class JsonParser(Parser):
            _spaces = Any(*" \t\n\r") * REPEAT

            @(Str('"') + ~Str('"') * REPEAT + Str('"').expect("Expected end of string")).set_factory
            @staticmethod
            def string(v):
                return "".join(v[1])

            number = Repeat(Any(*"0123456789"), mini=1, factory=lambda chars: int("".join(chars)))

            pair = (_spaces + string + _spaces + Str(":") + Var("value")).set_factory(lambda v: (v[1], v[4]))

            object = (Str("{") + pair*(0, None, ",") + Str("}").expect("Expected end of object"))\
                .set_factory(lambda v: dict(v[1]))

            list = (Str("[") + Var("value")*(0, None, ",") + Str("]").expect("Expected end of list"))\
                .set_factory(lambda v: v[1])

            __start__ = value = (_spaces+Any(string, number, object, list)+_spaces).set_factory(lambda v: v[1])

        self.assertEqual(JsonParser('{"a" : 1, "b":2 }'), {"a": 1, "b": 2})
        self.assertEqual(JsonParser("""
        {"aa": [1, 2, 3], 
        "bb": {"a": 1, "b": "2"}}
        """), {"aa": [1, 2, 3], "bb": {"a": 1, "b": "2"}})

    def test_indents(self):
        class IndentParser(Parser):
            INDENT_CHAR = Any(" ")
            indent = 0
            INDENT = INDENT_CHAR * Var("indent")
            LINE = ((INDENT + Not(Any(*":\n")) * MINI_1).set_factory(lambda v: "".join(v[1]))
                    + (Str(":\n") + UNS(Var("BLOCK"), indent=Var("indent").add(1))).set_factory(lambda v: v[1]) * OPT
                    ).set_factory(lambda v: [v[0]] + v[1])

            BLOCK = Repeat(LINE, mini=1, join="\n")
            __start__ = BLOCK

        #
        # class IndentParser(Parser, start="block"):
        #     indent = 0
        #     _char = " "
        #     line_start = Sequence(
        #         Repeat(_char, mini=Var("indent")),
        #         (~(Str("\n") | Str(":\n")) * MINI_1).set_factory("".join),
        #         factory=lambda v: v[1])
        #
        #     line = line_start\
        #         + ((Str(":\n")
        #            + UNS(Var("block"), indent=Var('indent').add(1))).set_factory(lambda v: v[1])*OPT
        #            ).set_factory(lambda v: (v[0] if v else []))
        #
        #     block = Repeat(line, join="\n")
        r = IndentParser.parse("""
aaa:
 hhh
bbb:
 ccc
"""[1:-1])
        # from json import dumps
        # print(dumps(r, indent=4))
        # print(r)
