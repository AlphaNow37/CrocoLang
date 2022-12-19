import code_creator
from croco.parser.first_pass import FirstPassCtx
from croco.parser import expr
from croco.parser.consts import OP_TO_NAME


class Statement:
    _show_clsname_in_repr = True

    filename = None

    def __init__(self, line):
        self.line = line

    def _repr(self):
        return "???"

    def __repr__(self):
        if self._show_clsname_in_repr:
            return f"{self.__class__.__name__}({self._repr()}, {self.line})"
        return f"<{self._repr()} at {self.line}>"

    def to_stmt_code(self, gen: code_creator.CodeGenerator):
        print(self)
        raise NotImplementedError

    def optimize(self):
        return self

    def first_pass(self, ctx: FirstPassCtx):
        self.filename = ctx.filename
        return self

class Affectation(Statement):
    _show_clsname_in_repr = False

    def __init__(self, variable, value, line, inplace_op=None):
        if isinstance(variable, expr.Constant):
            raise SyntaxError("Cannot affect a constant")
        elif isinstance(variable, expr.Call):
            raise SyntaxError("Cannot affect a function call")
        elif not isinstance(variable, expr.VarName | expr.SecondLevel):
            raise SyntaxError("Cannot affect a non-variable")
        self.variable = variable
        self.value = value
        self.inplace_op = inplace_op
        super().__init__(line)

    def _repr(self):
        return f"{self.variable} {self.inplace_op or ''}= {self.value}"

    @classmethod
    def from_toks(cls, toklist):
        match toklist:
            case [var, [], "=" as eq, value]:
                return cls(var, value, eq.start_line)
            case [var, [inplace_op], "=" as eq, value]:
                return cls(var, value, eq.start_line, inplace_op=inplace_op)
            case _:
                raise SyntaxError("Invalid affectation " + str(toklist))

    def to_stmt_code(self, gen: code_creator.CodeGenerator):
        if self.inplace_op is not None:
            self.variable.to_expr_code(gen)
            self.value.to_expr_code(gen)
            gen += f"INPLACE_{OP_TO_NAME[self.inplace_op]}"
        else:
            self.value.to_expr_code(gen)
        self.variable.store(gen)

    def first_pass(self, ctx: FirstPassCtx):
        if isinstance(self.variable, expr.VarName):
            ctx.vars.add(self.variable.name)
        self.value.first_pass(ctx)
        self.variable.first_pass(ctx)
