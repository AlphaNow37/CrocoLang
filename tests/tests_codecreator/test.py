import unittest
import opcode

import code_creator


class TestCodeCreator(unittest.TestCase):
    def test_basics(self):
        gen = code_creator.CodeGenerator(12, "test.py", "test")
        gen += "LOAD_GLOBAL", gen.name("print")
        code = gen.build()

        self.assertEqual(code.co_argcount, 0)
        self.assertEqual(code.co_posonlyargcount, 0)
        self.assertEqual(code.co_kwonlyargcount, 0)
        self.assertEqual(code.co_nlocals, 0)
        self.assertEqual(code.co_stacksize, 1)
        self.assertEqual(code.co_code, bytes([opcode.opmap["LOAD_GLOBAL"], code.co_names.index("print")]))
        self.assertEqual(code.co_consts, ())
        self.assertEqual(code.co_names, ("print",))
        self.assertEqual(code.co_varnames, ())
        self.assertEqual(code.co_filename, "test.py")
        self.assertEqual(code.co_name, "test")
        self.assertEqual(code.co_firstlineno, 12)

    def test_line_numbers(self):
        gen = code_creator.CodeGenerator()
        gen += "LOAD_GLOBAL", gen.name("print")
        gen.line += 1
        gen += "LOAD_CONST", gen.const("hoooy")
        gen.line = 5
        gen += "CALL_FUNCTION", 1
        gen += "RETURN_VALUE"
        code = gen.build()
        lines = list(code.co_lines())
        self.assertEqual(lines, [(0, 2, 0), (2, 4, 1), (4, 8, 5)])
        self.assertEqual(code.co_lnotab, bytes.fromhex("02 01 02 04"))

    def test_eval(self):
        gen = code_creator.CodeGenerator()
        gen += "LOAD_GLOBAL", gen.name("int")
        gen += "LOAD_CONST", gen.const("12")
        gen += "CALL_FUNCTION", 1
        gen += "RETURN_VALUE"
        code = gen.build()
        self.assertEqual(eval(code), 12)
