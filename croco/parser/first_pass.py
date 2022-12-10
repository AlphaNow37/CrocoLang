class FirstPassCtx:
    def __init__(self, filename):
        self.filename = filename
        self.vars = set()

def first_pass(tokens, filename):
    tokens = tokens.optimize()
    ctx = FirstPassCtx(filename)
    return tokens.first_pass(ctx)
