from croco.parser.stmt import Statement


class Block(Statement):
    def __init__(self, statements, line):
        self.statements = statements
        super().__init__(line)

    def _repr(self):
        return ", ".join(map(repr, self.statements))

    @classmethod
    def from_toks(cls, lines):
        lines = [smt for line in lines for smt in line]
        return cls(lines, lines[0].line)

    def first_pass(self, ctx):
        super().first_pass(ctx)
        for stmt in self.statements:
            stmt.first_pass(ctx)
        return self

    def optimize(self):
        self.statements = [stmt.optimize() for stmt in self.statements]
        return self

    def to_stmt_code(self, gen):
        for stmt in self.statements:
            stmt.to_stmt_code(gen)

class FlowControl(Statement):
    def __init__(self, block, line, else_clause=None):
        self.block = block
        self.else_clause = else_clause
        super().__init__(line)

    def first_pass(self, ctx):
        super().first_pass(ctx)
        self.block.first_pass(ctx)
        if self.else_clause:
            self.else_clause.first_pass(ctx)
        return self

    def optimize(self):
        self.block.optimize()
        return self

    def to_stmt_code(self, gen):
        self.end_partial = gen.partial()
        self.block.to_stmt_code(gen)

    def add_else_clause(self, gen):
        if self.else_clause:
            self.else_clause.to_stmt_code(gen)
        self.end_partial.set(gen.actual_ins_index)

class _ConditionLikeFlowControl(FlowControl):
    def __init__(self, expr, block, line):
        self.expr = expr
        super().__init__(block, line)

    @classmethod
    def from_toks(cls, toks):
        return cls(toks[1], None, toks[0].start_line)

    def first_pass(self, ctx):
        self.expr.first_pass(ctx)
        return super().first_pass(ctx)

class If(_ConditionLikeFlowControl):
    def __init__(self, expr, block, line):
        super().__init__(expr, block, line)

    def _repr(self):
        return f"if {self.expr}: {self.block}"

    def to_stmt_code(self, gen):
        self.expr.to_expr_code(gen)
        with gen.jump_to("POP_JUMP_IF_FALSE"):
            super().to_stmt_code(gen)
            if self.else_clause:
                gen += "JUMP_ABSOLUTE", self.end_partial
        super().add_else_clause(gen)

class While(_ConditionLikeFlowControl):
    def _repr(self):
        return f"while {self.expr}: {self.block}"

    def to_stmt_code(self, gen):
        with gen.jump_abs_back():
            self.expr.to_expr_code(gen)
            with gen.jump_to("POP_JUMP_IF_FALSE", add=1):
                super().to_stmt_code(gen)
        self.add_else_clause(gen)

class For(FlowControl):
    def __init__(self, var, expr, block, line):
        self.expr = expr
        self.var = var
        super().__init__(block, line)

    def _repr(self):
        return f"for {self.expr}: {self.block}"

    @classmethod
    def from_toks(cls, toks):
        return cls(toks[1], toks[3], None, toks[0].start_line)

    def to_stmt_code(self, gen):
        self.expr.to_expr_code(gen)
        gen += "GET_ITER"
        with gen.jump_abs_back(), gen.jump_forward("FOR_ITER", add=1):
            self.var.store(gen)
            super().to_stmt_code(gen)
        self.add_else_clause(gen)

    def first_pass(self, ctx):
        self.expr.first_pass(ctx)
        self.var.first_pass(ctx)
        return super().first_pass(ctx)
