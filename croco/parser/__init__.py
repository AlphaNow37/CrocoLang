
import parser_v2 as P
from croco.parser import expr, stmt, blocks, encoder, first_pass

def second_level(toklist):
    value = toklist[0]
    for tok in toklist[1]:
        tok.obj = value
        value = tok
    return value

def assign_block(toklist):
    match toklist:
        case [_, blocks.FlowControl() as flow_control, ":" as dbpoints, (list() as ins, True | "\n")]:
            block = blocks.Block(ins, dbpoints.start_line)
        case [_, blocks.FlowControl() as flow_control, ":" as dbpoints, ("\n", blocks.Block() as block)]:
            block.line = dbpoints.start_line
        case _:
            print(toklist)
            raise Exception("Not a block")
    flow_control.block = block
    return [flow_control]

def join_elses(toklist):
    block, elifs, else_ = toklist
    last = block[0]
    for [elif_] in elifs:
        last.else_clause = elif_
        last = elif_
    if else_:
        last.else_clause = else_[0][0]
    return block

INLINE_SPACES = P.Any(*" \t") * P.REPEAT
MULTILINE_SPACES = (P.Any(*" \t\n\r") * P.REPEAT).set_factory(lambda v: "")
def bracketed(value, brackets="()"):
    return P.Sequence(
        brackets[0],
        P.UNS(
            value,
            SPACES=MULTILINE_SPACES,
        ),
        P.Expected(brackets[1], "Expected closing parenthesis line {i.line}"),
    ).set_factory(lambda v: v, indexes=[1])

def _spacable(v):
    return P.Sequence(P.Var("SPACES"), v, P.Var("SPACES")).set_factory(lambda v: v, indexes=[1])

def operator(ops, sup):
    return (sup + (
            P.SaveAs(P.Any(*ops), "last_op") + sup.expect("Expected expression after operator {ns[last_op]} line {i.line}")
    ) * P.REPEAT).set_factory(expr.Op.from_toks)



def parser():
    SPACES = INLINE_SPACES

    NUMBER = (P.Any(*"0123456789") * P.MINI_1).set_factory(expr.Number.from_toks)
    STRING = P.Sequence(
        P.SaveAs(P.Any(*"'\""), "quote_char"),
        ~(P.Var("quote_char")) * P.REPEAT,
        P.Var("quote_char").expect("Unclosed quote {ns['quote_char']}"),
        factory=expr.String.from_toks)

    CONSTANT = NUMBER | STRING
    IDENTIFIER = (P.Any(*"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_") * P.MINI_1).set_factory(
        expr.VarName.from_toks)
    SPACED_IDENTIFIER = _spacable(IDENTIFIER)

    FIRST_LEVEL = _spacable(CONSTANT | IDENTIFIER | bracketed(P.Var("EXPRESSION")))
    GETATTR = P.Sequence(".", SPACED_IDENTIFIER).set_factory(expr.GetAttr.from_toks)
    CALL = bracketed(P.Var("EXPRESSION") * (0, None, ",")).set_factory(expr.Call.from_toks, indexes=[0, 1])
    GETITEM = bracketed(P.Var("EXPRESSION"), "[]").set_factory(expr.GetItem.from_toks, indexes=[0, 1])
    SECOND_LEVEL = (FIRST_LEVEL + (GETATTR | CALL | GETITEM) * P.REPEAT).set_factory(second_level)

    EXPONENT = operator(["**"], SECOND_LEVEL)
    MULTIPLICATION = operator("*/", EXPONENT)
    ADDITION = operator("+-", MULTIPLICATION)

    EXPRESSION = (
        ADDITION
    )
    EXPECTED_EXPR = EXPRESSION.expect("expected an expression")

    _INPLACE_OP = P.Any(*"+-*/%@|&") | "//" | "**"
    AFFECTABLE = SECOND_LEVEL
    AFFECTATION = (AFFECTABLE + _INPLACE_OP*P.OPT + "=" + EXPRESSION).set_factory(stmt.Affectation.from_toks)

    STATEMENT = (
        AFFECTATION
        | EXPRESSION
    )

    indent = 0
    _INDENT_CHARS = P.Any(*" \t")
    INDENT = (P.Repeat(
        _INDENT_CHARS, mini=P.Var("indent"), maxi=P.Var("indent")
    ) + P.Not(_INDENT_CHARS, increment=0).expect("Too many indentations line {i.line} {i.column}")
              ).set_factory(lambda v: "")

    LINE = (INDENT + P.Repeat(STATEMENT, join=";") + (P.END | "\n")).set_factory(lambda v: v[1])
    EMPTY_LINE = (INLINE_SPACES + (P.END | "\n")).set_factory(lambda v: "")

    IF = P.Sequence("if", EXPECTED_EXPR, factory=blocks.If.from_toks)

    WHILE = P.Sequence("while", EXPECTED_EXPR, factory=blocks.While.from_toks)
    FOR = P.Sequence("for", AFFECTABLE, "in", EXPRESSION, factory=blocks.For.from_toks)

    ELIF = P.Sequence("elif", EXPRESSION, factory=blocks.If.from_toks)
    ELSE = P.Sequence("else", factory=lambda toklist: blocks.FlowControl(None, toklist[0].start_line))

    def _make_flowcontrol(line):
        return (INDENT + line + ":" + (
                (P.Repeat(STATEMENT, join=";", mini=1) + (P.END | "\n"))
                | P.Str("\n") + P.UNS(P.Var("BLOCK").expect("Expected a block, line {i.line}"),
                                      indent=P.Var("indent").add(1)))
         ).set_factory(assign_block)

    FLOW_CONTROL = (_make_flowcontrol(IF | WHILE | FOR)
                    + _make_flowcontrol(ELIF) * P.REPEAT
                    + _make_flowcontrol(ELSE) * P.OPT).set_factory(join_elses)

    BLOCK = ((LINE | EMPTY_LINE | FLOW_CONTROL) * P.MINI_1).set_factory(blocks.Block.from_toks)

    return type("CrocoParser", (P.Parser,), locals(), start=BLOCK)


crocoparser = parser()

def croco_compile(code, filename="Unkown"):
    tokens = crocoparser(code)
    tokens = first_pass.first_pass(tokens, filename)
    return encoder.to_code(tokens)

def run(code, filename="Unkown"):
    code = croco_compile(code, filename)
    print("___")
    return exec(code)

if __name__ == '__main__':
    code = """
a = 0
if a:
    print("hello")
print("hey")
""".removeprefix("\n").removesuffix("\n").replace(" "*4, "\t")
    compiled = compile(code, "test", "exec")
    import dis
    dis.dis(compiled)
    # print(dis.code_info(compiled))
    # print(compiled.co_lnotab.hex(" "))
    # print(compiled.co_code.hex(" "))
    # print(len(compiled.co_code)-4)
    lines = crocoparser(code)
    print(lines)
    run(code)
