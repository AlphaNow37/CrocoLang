from croco.__main__ import main

from croco.parser import croco_compile, run
from croco.parser.repl import Repl

def run_repl():
    Repl().run()
