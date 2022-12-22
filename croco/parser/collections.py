from croco.parser.expr import Expr


class CollectionLitteral(Expr):
    def __init__(self, *exprs, ctype, line):
        self.exprs = exprs
        self.ctype = ctype
        super().__init__(line)

    @classmethod
    def from_toks(cls, toks, close_bracket):
        exprs = toks[0]
        match close_bracket:
            case ")": ctype = "tuple"
            case "]": ctype = "list"
            case "}": ctype = "set"
            case _: raise ValueError(f"Unknown collection type {close_bracket}")
        return cls(*exprs, ctype=ctype, line=close_bracket.start_line)

    def to_expr_code(self, gen):
        for expr in self.exprs:
            expr.to_expr_code(gen)
        super().to_expr_code(gen)
        gen += f"BUILD_{self.ctype.upper()}", len(self.exprs)

    def first_pass(self, ctx):
        for expr in self.exprs:
            expr.first_pass(ctx)

    def store(self, gen):
        raise NotImplementedError()

def get_tuple(toks):
    match toks:
        case [expr, []]:
            return expr
        case [expr, pairs]:
            return CollectionLitteral(expr, *(pair[1] for pair in pairs), ctype="tuple", line=pairs[-1][1].line)
        case _:
            raise ValueError("Unkown tuple")
