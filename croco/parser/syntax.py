from croco.parser import expr, stmt, blocks

import parser_v2 as P

LETETRS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
DIGITS = "0123456789"

def second_level(toklist):
    value = toklist[0]
    for tok in toklist[1]:
        tok.obj = value
        value = tok
    return value

def assign_block(toklist):
    match toklist:
        case [_, blocks.FlowControl() as flow_control, ":" as dbpoints, _, (list() as ins, True | "\n")]:
            block = blocks.Block(ins, dbpoints.start_line)
        case [_, blocks.FlowControl() as flow_control, ":" as dbpoints, _, ("\n", blocks.Block() as block)]:
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

INLINE_SPACES = P.Any(*" \t", "\\\n") * P.REPEAT
COMMENT = P.Str("#") + P.Not(P.END | "\n") * P.REPEAT
MULTILINE_SPACES = (P.Any(*" \t\n\r", COMMENT) * P.REPEAT).set_factory(lambda v: "")

def bracketed(value, brackets="()"):
    def fmt(ns, *_, **__):  # Used because str.format() don't use normal expression, i can't add 1 ...
        return f"Expected closing '{brackets[0]}', opened line {ns['bracket_opening'].start_line + 1}"
    fmt.format = fmt

    return P.Sequence(
        P.SaveAs(brackets[0], "bracket_opening"),
        P.UNS(
            value,
            SPACES=MULTILINE_SPACES,
        ),
        P.Expected(brackets[1], fmt),
    ).set_factory(lambda v: v, indexes=[1])

def _spacable(v):
    return P.Sequence(P.Var("SPACES"), v, P.Var("SPACES")).set_factory(lambda v: v, indexes=[1])

def operator(ops, sup, factory=expr.Op.from_toks):
    return (sup + (
            P.SaveAs(P.Any(*ops), "last_op") + sup.expect("Expected expression after operator {ns[last_op]} line {i.line}")
    ) * P.REPEAT).set_factory(factory)


def parser():
    SPACES = INLINE_SPACES

    _DIGIT = P.Any(*DIGITS)
    INT = (_DIGIT * P.MINI_1).set_factory(expr.Int.from_toks)
    FLOAT = ((_DIGIT * P.MINI_1 + "." + _DIGIT * P.REPEAT)
             | ("." + _DIGIT * P.MINI_1)).set_factory(expr.Float.from_toks, )
    STRING = P.Sequence(
        P.SaveAs(P.Any(*"'\""), "quote_char"),
        ~(P.Var("quote_char")) * P.REPEAT,
        P.Var("quote_char").expect("Unclosed quote '{ns[quote_char]}'"),
        factory=expr.String.from_toks)


    CONSTANT = FLOAT | INT | STRING
    IDENTIFIER = (P.Any(*LETETRS) + P.Any(*LETETRS, *DIGITS)*P.REPEAT).set_factory(
        expr.VarName.from_toks)
    SPACED_IDENTIFIER = _spacable(IDENTIFIER)

    FIRST_LEVEL = _spacable(CONSTANT | IDENTIFIER | bracketed(P.Var("EXPRESSION")))
    GETATTR = P.Sequence(".", SPACED_IDENTIFIER).set_factory(expr.GetAttr.from_toks)
    CALL = bracketed(P.Var("EXPRESSION") * (0, None, ",")).set_factory(expr.Call.from_toks, indexes=[0, 1])
    GETITEM = bracketed(P.Var("EXPRESSION"), "[]").set_factory(expr.GetItem.from_toks, indexes=[0, 1])
    SECOND_LEVEL = (FIRST_LEVEL + _spacable(GETATTR | CALL | GETITEM) * P.REPEAT).set_factory(second_level)

    EXPONENT = operator(["**"], SECOND_LEVEL)
    MULTIPLICATION = operator(["*", "//", "/", "%"], EXPONENT)
    ADDITION = operator("+-", MULTIPLICATION)
    COMPARISON = operator(("<=", "<", ">=", ">", "!=", "=="), ADDITION, factory=expr.CmpOp.from_toks)

    EXPRESSION = (
        COMPARISON
    )
    EXPECTED_EXPR = EXPRESSION.expect("expected an expression")

    _INPLACE_OP = P.Any(*"+-*/%@|&") | "//" | "**"
    AFFECTABLE = SECOND_LEVEL
    AFFECTATION = (AFFECTABLE + _INPLACE_OP*P.OPT + "=" + EXPECTED_EXPR).set_factory(stmt.Affectation.from_toks)

    BREAK = P.Str("break").set_factory(blocks.Break.from_toks)
    CONTINUE = P.Str("continue").set_factory(blocks.Continue.from_toks)
    PASS = P.Str("pass").set_factory(stmt.Pass.from_toks)

    STATEMENT = ((
        BREAK | CONTINUE | PASS
        | AFFECTATION
        | EXPRESSION
    ) )# + INLINE_SPACES*P.REPEAT).set_factory(lambda v: v[0])

    indent = 0
    _INDENT_CHARS = P.Any(" "*4, "\t")
    INDENT = (P.Repeat(
        _INDENT_CHARS, mini=P.Var("indent"), maxi=P.Var("indent")
    ) + P.Not(_INDENT_CHARS, increment=0).expect("Too many indentations line {line} col {col}", etype=IndentationError)
              ).set_factory(lambda v: "")

    LINE = (INDENT + P.Repeat(STATEMENT, join=";") + COMMENT*P.OPT + (P.END | "\n")).set_factory(lambda v: v[1])
    EMPTY_LINE = (INLINE_SPACES + (P.END | "\n")).set_factory(lambda v: "")

    IF = P.Sequence("if", EXPECTED_EXPR, factory=blocks.If.from_toks)

    WHILE = P.Sequence("while", EXPECTED_EXPR, factory=blocks.While.from_toks)
    FOR = P.Sequence("for", AFFECTABLE, "in", EXPRESSION, factory=blocks.For.from_toks)

    ELIF = P.Sequence("elif", EXPRESSION, factory=blocks.If.from_toks)
    ELSE = P.Sequence("else", factory=lambda toklist: blocks.FlowControl(None, toklist[0].start_line))

    def _make_flowcontrol(line):
        return (INDENT + line + ":" + INLINE_SPACES * P.REPEAT +  (
                (P.Repeat(STATEMENT, join=";", mini=1) + (P.END | "\n"))
                | P.Str("\n") + P.UNS(P.Var("BLOCK").expect("Expected a block, line {line}"),
                                      indent=P.Var("indent").add(1)))
         ).set_factory(assign_block)

    FLOW_CONTROL = (_make_flowcontrol(IF | WHILE | FOR)
                    + _make_flowcontrol(ELIF) * P.REPEAT
                    + _make_flowcontrol(ELSE) * P.OPT).set_factory(join_elses)

    BLOCK = ((EMPTY_LINE | LINE | FLOW_CONTROL) * P.MINI_1).set_factory(blocks.Block.from_toks)

    return type("CrocoParser", (P.Parser,), locals(), start=BLOCK)


crocoparser = parser()