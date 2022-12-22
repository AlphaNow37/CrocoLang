import opcode

import code_creator

from croco.parser.blocks import Block

def _get_jump_target(gen, act_i: int) -> int:
    ins = gen.cast_to_int(gen.instructions[act_i])
    arg = gen.cast_to_int(gen.instructions[act_i+1])
    name = opcode.opname[ins]
    match name:
        case ("JUMP_ABSOLUTE"
              | "POP_JUMP_IF_FALSE" | "POP_JUMP_IF_TRUE"
              | "JUMP_IF_FALSE_OR_POP" | "JUMP_IF_TRUE_OR_POP"):
            return arg * 2
        case "JUMP_IF_NOT_EXC_MATCH":
            raise NotImplementedError()
        case "JUMP_FORWARD":
            return act_i + arg * 2 + 2
        case _:
            return -1

def to_code(tokens: Block, as_expr = False):
    gen = code_creator.CodeGenerator(1, filename=tokens.filename)
    tokens.to_stmt_code(gen)
    if (
            as_expr
            and len(gen.instructions) > 2
            and gen.instructions[-2] == opcode.opmap["POP_TOP"]
            and all(_get_jump_target(gen, i) < len(gen.instructions)
                    for i in range(0, len(gen.instructions), 2))
    ):
        gen.instructions = gen.instructions[:-2]
    else:
        gen += "LOAD_CONST", gen.const(None)
    gen += "RETURN_VALUE"
    build = gen.build()
    # import dis
    # dis.dis(build)
    # print(dis.code_info(build))
    return build
