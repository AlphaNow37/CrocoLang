"""
Interactive REPL for Croco.
"""

import traceback
import time

from parser_v2 import CharStream

from croco.parser import croco_compile
import linecache


class Repl:
    def __init__(self):
        self.globals = {}

    def add_in_cache(self, stream):
        linecache.cache["<repl>"] = (
            len(stream.buffer),  # size (number of char)
            None, # mtime
            stream.buffer.splitlines(True), # lines list
            "<repl>")

    def run(self):
        while True:
            stream = CharStream(self.ask_input)
            self.next_prefix = ">>> "
            try:
                code = croco_compile(stream, filename="<repl>", mode="eval")
            except SyntaxError as e:
                self.add_in_cache(stream)
                traceback.print_exc()
                time.sleep(0.1)
                continue
            self.add_in_cache(stream)
            try:
                res = eval(code, self.globals)
            except SystemExit:
                break
            except BaseException:
                traceback.print_exc()
                time.sleep(0.1)
            else:
                if res is not None:
                    print(res)

    def ask_input(self):
        s = input(self.next_prefix)
        self.next_prefix = "... "
        if not s:
            return None
        return s + "\n"


if __name__ == '__main__':
    Repl().run()
