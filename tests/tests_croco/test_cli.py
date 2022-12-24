import subprocess
import unittest

CMD = ["python", r"D:\dossier\telechargement\dossier\dossiers\PycharmProjects\AlphaParse\croco"]

class TestCli(unittest.TestCase):
    def test_repl(self):
        tests = {
            "1+1": "2",
            "None": "",
            "print('hey')": "hey",
        }
        for code, expected in tests.items():
            with self.subTest(code=code):
                p = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate(input=code.encode()+b"\n\r")
                out = stdout.decode().removesuffix("\r\n>>> ")
                err = stderr.decode()
                self.assertTrue(out.endswith("\r\n"+expected), f"out={out!r}, expected={expected!r}, err={err!r}")
