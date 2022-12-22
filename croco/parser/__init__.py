from croco.parser import expr, stmt, blocks, encoder, first_pass
from croco.parser.syntax import crocoparser

def croco_compile(code, filename="Unkown", mode="exec"):
    try:
        tokens = crocoparser(code)
        tokens = first_pass.first_pass(tokens, filename)
        return encoder.to_code(tokens, as_expr=mode == "eval")
    except SyntaxError as e:
        e.filename = filename
        e.text = code.split("\n")[e.lineno - 1]
        raise

def run(code, filename="Unkown", mode="exec"):
    code = croco_compile(code, filename, mode=mode)
    import dis, opcode
    dis.dis(code)
    print(code.co_code, len(code.co_code))
    print([opcode.opname[i] for i in code.co_code[::2]])
    return exec(code) if mode == "exec" else eval(code)

if __name__ == '__main__':
    code = """
while True:pass
""".removeprefix("\n").removesuffix("\n").replace(" "*4, "\t")
    compiled = compile(code, "test", "exec")
    # exec (compiled)
    import dis
    dis.dis(compiled)
    # print(dis.code_info(compiled))
    # print(compiled.co_lnotab.hex(" "))
    # # print(compiled.co_code.hex(" "))
    # # print(len(compiled.co_code)-4)
    lines = crocoparser(code)
    print(lines)
    run(code)
