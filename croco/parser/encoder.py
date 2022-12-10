import code_creator

from croco.parser.blocks import Block


def to_code(tokens: Block):
    gen = code_creator.CodeGenerator(1, filename=tokens.filename)
    tokens.to_stmt_code(gen)
    gen += "LOAD_CONST", gen.const(None)
    gen += "RETURN_VALUE"
    build = gen.build()
    import dis
    dis.dis(build)
    print(dis.code_info(build))
    return build
