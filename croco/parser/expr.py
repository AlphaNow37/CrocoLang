from opcode import cmp_op

from code_creator import CodeGenerator

from croco.parser.stmt import Statement
from croco.parser.consts import OP_TO_NAME

class Expr(Statement):
    def to_expr_code(self, gen: CodeGenerator):
        gen.line = self.line

    def to_stmt_code(self, gen: CodeGenerator):
        self.to_expr_code(gen)
        gen += "POP_TOP"

    def store(self, gen: CodeGenerator):
        raise NotImplementedError()

class Constant(Expr):
    def __init__(self, value, line):
        self.value = value
        super(Constant, self).__init__(line)

    def _repr(self):
        return self.value

    def to_expr_code(self, gen: CodeGenerator):
        super().to_expr_code(gen)
        gen += "LOAD_CONST", gen.const(self.value)

    def store(self, gen):
        raise SyntaxError("Cannot assign to a constant")

class Int(Constant):
    @classmethod
    def from_toks(cls, toklist):
        return cls(int("".join(toklist)), toklist[0].start_line)

class Float(Constant):
    @classmethod
    def from_toks(cls, toklist):
        match toklist:
            case [left, "." as p, right]:
                return cls(float("".join(left) + "." + "".join(right)), p.start_line)
            case ["." as p, right]:
                return cls(float("." + "".join(right)), p.start_line)
            case _:
                raise SyntaxError("Invalid float literal")

class String(Constant):
    @classmethod
    def from_toks(cls, toklist):
        return cls("".join(toklist[1]), toklist[0].start_line)

class VarName(Expr):
    def __init__(self, name, line):
        self.name = name
        super().__init__(line)

    def _repr(self):
        return self.name

    @classmethod
    def from_toks(cls, toklist):
        return cls(toklist[0]+"".join(toklist[1]), toklist[0].start_line)

    def first_pass(self, ctx):
        self.ctx = ctx
        return super().first_pass(ctx)

    def to_expr_code(self, gen: CodeGenerator):
        super().to_expr_code(gen)
        if self.name in self.ctx.vars:
            gen += "LOAD_NAME", gen.name(self.name)
        else:
            gen += "LOAD_NAME", gen.name(self.name)

    def store(self, gen):
        if self.name in self.ctx.vars:
            gen += "STORE_NAME", gen.name(self.name)
        else:
            gen += "STORE_NAME", gen.name(self.name)

class Op(Expr):
    _show_clsname_in_repr = False

    def __init__(self, left, right, op, line):
        self.left = left
        self.right = right
        self.op = op
        super().__init__(line)

    @classmethod
    def from_toks(cls, toklist):
        first, after = toklist
        if not after:
            return first
        op, second = after[0]
        obj = cls(first, second, op, op.start_line)
        return cls.from_toks([obj, after[1:]])

    def _repr(self):
        return f"{self.left} {self.op} {self.right}"

    def to_expr_code(self, gen: CodeGenerator):
        super().to_expr_code(gen)
        self.left.to_expr_code(gen)
        self.right.to_expr_code(gen)
        gen += f"BINARY_{OP_TO_NAME[self.op]}"

    def store(self, gen):
        raise SyntaxError("Cannot assign to an operation")

    def first_pass(self, ctx):
        self.left.first_pass(ctx)
        self.right.first_pass(ctx)
        return super().first_pass(ctx)

class CmpOp(Expr):
    def __init__(self, parts, ops, line):
        super().__init__(line)
        self.parts: list[Expr] = parts
        self.ops: list[str] = ops
        assert len(self.parts) == len(self.ops) + 1

    def first_pass(self, ctx):
        for part in self.parts:
            part.first_pass(ctx)
        return super().first_pass(ctx)

    def _repr(self):
        return str(self.parts[0]) + "".join(f" {op} {part}" for op, part in zip(self.ops, self.parts[1:]))

    @classmethod
    def from_toks(cls, toklist):
        if not toklist[1]:
            return toklist[0]
        parts = [toklist[0]]
        ops = []
        for op, part in toklist[1]:
            ops.append(op)
            parts.append(part)
        return cls(parts, ops, toklist[0].line)


    def to_expr_code(self, gen: CodeGenerator):
        Expr.to_expr_code(self, gen)
        end = gen.partial()
        self.parts[0].to_expr_code(gen)
        for i, (op, part) in enumerate(zip(self.ops, self.parts[1:])):
            part.to_expr_code(gen)
            if i != len(self.ops) - 1:
                gen += "DUP_TOP"
                gen += "ROT_THREE"
            gen += f"COMPARE_OP", cmp_op.index(op)
            if i == len(self.ops) - 1:
                gen += "JUMP_FORWARD", 2
            else:
                gen += "JUMP_IF_FALSE_OR_POP", end
        end.set(gen.actual_ins_index)
        gen += "ROT_TWO"
        gen += "POP_TOP"


    def store(self, gen):
        raise SyntaxError("Cannot assign to a comparison")


class SecondLevel(Expr):
    def __init__(self, line, obj=None):
        self.obj = obj
        super().__init__(line)

    def to_expr_code(self, gen: CodeGenerator):
        super().to_expr_code(gen)
        self.obj.to_expr_code(gen)

    def store(self, gen):
        self.obj.to_expr_code(gen)

    def first_pass(self, ctx):
        self.obj.first_pass(ctx)
        return super().first_pass(ctx)

class GetAttr(SecondLevel):
    def __init__(self, obj, attr, line):
        self.attr = attr
        super().__init__(line, obj)

    def _repr(self):
        return f"{self.obj}.{self.attr}"

    @classmethod
    def from_toks(cls, toklist):
        return GetAttr(None, toklist[1].name, toklist[0].start_line)

    def to_expr_code(self, gen: CodeGenerator):
        super().to_expr_code(gen)
        gen += "LOAD_ATTR", gen.name(self.attr)

    def store(self, gen):
        super().store(gen)
        gen += "STORE_ATTR", gen.name(self.attr)

class GetItem(SecondLevel):
    def __init__(self, obj, index, line):
        self.index = index
        super().__init__(line, obj)

    def _repr(self):
        return f"{self.obj}[{self.index}]"

    @classmethod
    def from_toks(cls, bracket, item):
        return cls(None, item, bracket.start_line)

    def to_expr_code(self, gen: CodeGenerator):
        super().to_expr_code(gen)
        self.index.to_expr_code(gen)
        gen += "BINARY_SUBSCR"

    def store(self, gen):
        super().store(gen)
        self.index.to_expr_code(gen)
        gen += "STORE_SUBSCR"

    def first_pass(self, ctx):
        self.index.first_pass(ctx)
        return super().first_pass(ctx)

class Call(SecondLevel):
    def __init__(self, obj, args, line):
        self.args = args
        super().__init__(line, obj)

    def _repr(self):
        return f"{self.obj}({', '.join(map(str, self.args))})"

    @classmethod
    def from_toks(cls, bracket, toklist):
        return Call(None, toklist, bracket.start_line)

    def to_expr_code(self, gen: CodeGenerator):
        super().to_expr_code(gen)
        for arg in self.args:
            arg.to_expr_code(gen)
        gen += "CALL_FUNCTION", len(self.args)

    def store(self, gen):
        raise SyntaxError("Cannot assign to a function call")

    def first_pass(self, ctx):
        for arg in self.args:
            arg.first_pass(ctx)
        return super().first_pass(ctx)
