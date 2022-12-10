import unittest
from pathlib import Path

import pycompile

from tests.tests_pycompile import a

HOME = Path(__file__).parent

class Test(unittest.TestCase):
    def test_a(self):
        self.assertEqual(a.t(), 12)

    def test_get_pycpath(self):
        path = pycompile.get_pyc_path(HOME / "a.py")
        self.assertEqual(path.suffix, ".pyc")
        self.assertEqual(path.name, "a.cpython-310.pyc")
        self.assertEqual(path.parent.name, "__pycache__")
        self.assertTrue(path.parent.is_dir())
        self.assertTrue(path.is_file())
        self.assertTrue(path.exists())

    def test_get_cachepath(self):
        path = pycompile.get_cache_path(pycompile.get_pyc_path(HOME / "a.py"))
        self.assertEqual(path.suffix, ".cache")
        self.assertEqual(path.name, "a.cpython-310.pyc.cache")
        self.assertEqual(path.parent.name, "__pycache__")
        self.assertTrue(path.parent.is_dir())
        self.assertFalse(path.exists())

    def test_load_pyc(self):
        code = pycompile.load_pyc(pycompile.get_pyc_path(HOME / "a.py"))
        self.assertTrue(code)
        self.assertEqual(code.co_filename, str(HOME / "a.py"))

    def test_create_file(self):
        code = pycompile.load_pyc(pycompile.get_pyc_path(HOME / "a.py"))
        pycompile.create_file(HOME / "b.py", code, initial_path=HOME / "a.py", force_recreate=True)
        self.assertTrue((HOME / "b.py").is_file())
        self.assertTrue((HOME / "b.py").exists())
        code2 = pycompile.load_pyc(pycompile.get_pyc_path(HOME / "b.py"))
        self.assertTrue(code2)

    def test_import(self):
        code = pycompile.load_pyc(pycompile.get_pyc_path(HOME / "a.py"))
        pycompile.create_file(HOME / "b.py", code, initial_path=HOME / "a.py")
        try:
            from tests.tests_pycompile import b
        except Exception as e:
            self.fail(e)
        else:
            self.assertTrue(b)
            self.assertEqual(b.t(), 12)
        # import dis
        # dis.dis(code)
        # print(dis.code_info(code))
        # print()
        # print(dis.code_info(code.co_consts[1]))
