from croco.parser import expr, stmt, blocks, collections

import parser_v2 as P

LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
DIGITS = "0123456789"

def _convert_second_level(toklist):
    """Convert a list of a [b] [c] ... into a tree getitem(getitem(a, b), c)"""
    value = toklist[0]
    for tok in toklist[1]:
        tok.obj = value
        value = tok
    return value

def _get_block(toklist):
    """Assign his block code to a flow control statement"""
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

def _add_elses(toklist):
    """Transform a list of if/elif/else into a tree of if/else(if/else)"""
    block, elifs, else_ = toklist
    last = block[0]
    for [elif_] in elifs:
        last.else_clause = elif_
        last = elif_
    if else_:
        last.else_clause = else_[0][0]
    return block



def _bracketed(value, brackets="()", indexes=(1,)):
    """A value surrounded by brackets"""
    def fmt(ns, *_, **__):  # Used because str.format() don't use normal expression, i can't add 1 ...
        return f"Expected closing '{brackets[0]}', opened line {ns['bracket_opening'].start_line + 1}"
    fmt.format = fmt

    return P.Sequence(
        P.SaveAs(brackets[0], "bracket_opening"),
        P.UNS(
            value,
            SPACES=P.Var("MULTILINE_SPACES"),
        ),
        P.Expected(brackets[1], fmt),
    ).set_factory(lambda v: v, indexes=indexes)

def _spacable(v):
    """An expression that can be surrounded by spaces"""
    return P.Sequence(P.Var("SPACES"), v, P.Var("SPACES")).set_factory(lambda v: v, indexes=[1])

def _operator(ops, sup, factory=expr.Op.from_toks):
    return (sup + (
            P.SaveAs(P.Any(*ops), "last_op") + sup.expect("Expected expression after operator {ns[last_op]} line {i.line}")
    ) * P.REPEAT).set_factory(factory)


def get_parser():
    # Spaces
    NEWLINE = P.Str("\n")
    INLINE_SPACES = P.Any(*" \t", "\\\n") * P.REPEAT
    COMMENT = P.Str("#") + P.Not(P.END | NEWLINE) * P.REPEAT
    MULTILINE_SPACES = (P.Any(*" \t\n\r", COMMENT) * P.REPEAT).set_factory(lambda v: "")

    SPACES = INLINE_SPACES  # Default in program; multiline in brackets

    # Vars, recursive
    TUPLE_EXPR = P.Var("TUPLE_EXPR")
    BASE_EXPR = P.Var("BASE_EXPR")
    EXPECTED_EXPR = P.Var("EXPECTED_EXPR")

    # Constants
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

    # Varnames
    IDENTIFIER = (P.Any(*LETTERS) + P.Any(*LETTERS, *DIGITS) * P.REPEAT).set_factory(
        expr.VarName.from_toks)
    SPACED_IDENTIFIER = _spacable(IDENTIFIER)  # With some spaces around

    COLL_LITERALS = P.Any(*[
        _bracketed(
            P.Repeat(P.Var("BASE_EXPR"), join=",")
            + P.Str(",")*P.OPT + MULTILINE_SPACES,
            brackets=brackets, indexes=[1, 2]
        ).set_factory(collections.CollectionLitteral.from_toks)
        for brackets in ("[]", "{}")
    ])

    # First level is the unit of the expression
    FIRST_LEVEL = _spacable(CONSTANT | IDENTIFIER | COLL_LITERALS | _bracketed(EXPECTED_EXPR))

    # Second level is a repetition of the first level, going lineary to the right: a[b].c(d) ...
    GETATTR = P.Sequence(".", SPACED_IDENTIFIER).set_factory(expr.GetAttr.from_toks)
    CALL = _bracketed(BASE_EXPR * (0, None, ",")).set_factory(expr.Call.from_toks, indexes=[0, 1])
    GETITEM = _bracketed(EXPECTED_EXPR, "[]").set_factory(expr.GetItem.from_toks, indexes=[0, 1])
    SECOND_LEVEL = (FIRST_LEVEL + _spacable(GETATTR | CALL | GETITEM) * P.REPEAT).set_factory(_convert_second_level)

    # Third level is the operators, in order of priority
    EXPONENT = _operator(["**"], SECOND_LEVEL)
    MULTIPLICATION = _operator(["*", "//", "/", "%"], EXPONENT)
    ADDITION = _operator("+-", MULTIPLICATION)
    BINSHIFTS = _operator(["<<", ">>"], ADDITION)
    BINAND = _operator("&", BINSHIFTS)
    BINXOR = _operator("^", BINAND)
    BINOR = _operator("|", BINXOR)
    COMPARISON = _operator(("<=", "<", ">=", ">", "!=", "=="), BINOR, factory=expr.CmpOp.from_toks)

    TUPLE_EXPR = (COMPARISON + (P.Str(",") + COMPARISON) * P.REPEAT).set_factory(collections.get_tuple)
    BASE_EXPR = COMPARISON

    EXPECTED_EXPR = TUPLE_EXPR.expect("expected an expression")

    # Assignments
    _INPLACE_OP = P.Any(*"+-*/%@|&") | "//" | "**"
    AFFECTABLE = SECOND_LEVEL
    AFFECTATION = (AFFECTABLE + _INPLACE_OP*P.OPT + "=" + P.Not("=", increment=0) + EXPECTED_EXPR).set_factory(stmt.Affectation.from_toks)

    # Statements
    BREAK = P.Str("break").set_factory(blocks.Break.from_toks)
    CONTINUE = P.Str("continue").set_factory(blocks.Continue.from_toks)
    PASS = P.Str("pass").set_factory(stmt.Pass.from_toks)

    STATEMENT = ((
        BREAK | CONTINUE | PASS
        | AFFECTATION
        | TUPLE_EXPR
    ) )# + INLINE_SPACES*P.REPEAT).set_factory(lambda v: v[0])

    # Blocks
    indent = 0
    _INDENT_CHARS = P.Any(" "*4, "\t")
    INDENT = (P.Repeat(
        _INDENT_CHARS, mini=P.Var("indent"), maxi=P.Var("indent")
    ) + P.Not(_INDENT_CHARS, increment=0).expect("Too many indentations line {line} col {col}", etype=IndentationError)
              ).set_factory(lambda v: "")


    END_OF_LINE = (P.Str(";") * P.OPT + (P.END | NEWLINE)).set_factory(lambda v: ...)
    LINE = (INDENT + P.Repeat(STATEMENT, join=";") + P.Str(";")*P.OPT + COMMENT*P.OPT + END_OF_LINE).set_factory(lambda v: v[1])

    EMPTY_LINE = (INLINE_SPACES + END_OF_LINE).set_factory(lambda v: "")

    # Flow controls
    IF = P.Sequence("if", EXPECTED_EXPR, factory=blocks.If.from_toks)

    WHILE = P.Sequence("while", EXPECTED_EXPR, factory=blocks.While.from_toks)
    FOR = P.Sequence("for", AFFECTABLE, "in", TUPLE_EXPR, factory=blocks.For.from_toks)

    ELIF = P.Sequence("elif", TUPLE_EXPR, factory=blocks.If.from_toks)
    ELSE = P.Sequence("else", factory=lambda toklist: blocks.FlowControl(None, toklist[0].start_line))

    def _make_flowcontrol(line):
        return (INDENT + line + ":" + INLINE_SPACES * P.REPEAT +  (
                (P.Repeat(STATEMENT, join=";", mini=1) + END_OF_LINE)
                | NEWLINE + P.UNS(P.Var("BLOCK").expect("Expected a block, line {line}"),
                                      indent=P.Var("indent").add(1)))
         ).set_factory(_get_block)

    FLOW_CONTROL = (_make_flowcontrol(IF | WHILE | FOR)
                    + _make_flowcontrol(ELIF) * P.REPEAT
                    + _make_flowcontrol(ELSE) * P.OPT).set_factory(_add_elses)

    BLOCK = ((EMPTY_LINE | LINE | FLOW_CONTROL) * P.MINI_1).set_factory(blocks.Block.from_toks)

    # Parser creation
    return type("CrocoParser", (P.Parser,), locals(), start=BLOCK)


crocoparser = get_parser()
