from contextlib import contextmanager

class FirstPassCtx:
    def __init__(self, filename):
        self.filename = filename
        self.vars = set()
        self.actual_loop = None
        self.actual_func = None

    @contextmanager
    def loop(self, loop):
        before = self.actual_loop
        self.actual_loop = loop
        yield
        self.actual_loop = before

    @contextmanager
    def func(self, func):
        before = self.actual_func
        self.actual_func = func
        yield
        self.actual_func = before

def first_pass(tokens, filename):
    tokens = tokens.optimize()
    ctx = FirstPassCtx(filename)
    return tokens.first_pass(ctx)
