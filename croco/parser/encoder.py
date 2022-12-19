import opcode

import code_creator

from croco.parser.blocks import Block


def to_code(tokens: Block, as_expr = False):
    gen = code_creator.CodeGenerator(1, filename=tokens.filename)
    tokens.to_stmt_code(gen)
    if as_expr and len(gen.instructions) > 2 and gen.instructions[-2] == opcode.opmap["POP_TOP"]:
        gen.instructions = gen.instructions[:-2]
    else:
        gen += "LOAD_CONST", gen.const(None)
    gen += "RETURN_VALUE"
    build = gen.build()
    # import dis
    # dis.dis(build)
    # print(dis.code_info(build))
    return build
