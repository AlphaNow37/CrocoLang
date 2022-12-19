from types import CodeType
from opcode import opmap, stack_effect, HAVE_ARGUMENT
from functools import partial
import contextlib

class Vue:
    def __init__(self, fieldname, value):
        self.fieldname = fieldname
        self.value = value

    def get_value(self, generator: "CodeGenerator"):
        fields = getattr(generator, self.fieldname)
        if self.value not in fields:
            fields.append(self.value)
        return fields.index(self.value)

class Partial:
    def __init__(self, value=None):
        self.set(value)

    def set(self, value):
        self.value = value

    def get(self):
        return self.value

class CodeGenerator:
    def __init__(self, firstlineno=0, filename="...", name="<module>"):
        self.filename = filename
        self.blockname = name
        self.firstlineno = firstlineno
        self.max_stacksize = 0
        self._stacksize = 0
        self.instructions = []

        self.lineotab = b''
        self._lineotab_last_ins = 0
        self._lineotab_last_delta_line = 0
        self.last_line = 0

    def update_stacksize(self, stacksize):
        self.max_stacksize = max(self.max_stacksize, stacksize)
        self._stacksize = stacksize

    stacksize = property(lambda self: self._stacksize, update_stacksize)

    var = partial(Vue, "varnames")
    name = partial(Vue, "names")
    const = partial(Vue, "constants")
    free = partial(Vue, "freevars")
    cell = partial(Vue, "cellvars")

    partial = Partial

    @contextlib.contextmanager
    def jump_forward(self, jump_ins, add=0):
        start = self.actual_ins_index
        self.add_ins(jump_ins, p := self.partial())
        yield
        p.set(self.actual_ins_index - start - 1 + add)

    @contextlib.contextmanager
    def jump_abs_back(self):
        start = self.actual_ins_index
        yield
        self.add_ins("JUMP_ABSOLUTE", start)

    @contextlib.contextmanager
    def jump_to(self, jump_ins, add=0):
        p = self.partial()
        self.add_ins(jump_ins, p)
        yield
        p.set(self.actual_ins_index + add)

    @property
    def actual_ins_index(self):
        return len(self.instructions) // 2  # 2 bytes per instruction

    def add_ins(self, opcode, arg: Vue | int = 0):
        if isinstance(opcode, str):
            opcode = opmap[opcode]
        self.instructions += [opcode, arg]
        if self.instructions[-2] >= HAVE_ARGUMENT:
            self.stacksize += stack_effect(opcode, arg if isinstance(arg, int) else 0)
        else:
            self.stacksize += stack_effect(opcode)

    def __add__(self, other):
        if isinstance(other, tuple):
            self.add_ins(*other)
        else:
            self.add_ins(other)
        return self

    def _add_to_lnotab(self, nins_delta, nlines_delta):
        self.lineotab += nins_delta.to_bytes(1, "little")
        while nlines_delta > 255:
            self.lineotab += b"\xff\x00"
            nlines_delta -= 255
        self.lineotab += nlines_delta.to_bytes(1, "little")

    def next_line(self, nlines=1):
        ins_delta = len(self.instructions) - self._lineotab_last_ins
        if ins_delta == 0:
            return
        elif ins_delta < 0:
            raise ValueError("Going backward in line indexes is not possible")
        self._add_to_lnotab(ins_delta, self._lineotab_last_delta_line)
        self._lineotab_last_ins = len(self.instructions)
        self._lineotab_last_delta_line = nlines
        self.last_line += nlines
        return self

    def go_line(self, lineno):
        self.next_line(lineno - self.last_line)
        self.last_line = lineno
        return self

    line = property(lambda self: self.last_line, go_line)

    def get_codebytes(self):
        b = bytearray()
        for i in self.instructions:
            if isinstance(i, int):
                b.append(i)
            elif isinstance(i, Vue):
                b.append(i.get_value(self))
            elif isinstance(i, Partial):
                b.append(i.get())
            else:
                raise ValueError(f"Unknown instruction type: {i}")
        return bytes(b)

    def build(self) -> CodeType:
        self.next_line(0)
        self.constants = []
        self.names = []
        self.varnames = []
        self.freevars = []
        self.cellvars = []
        codebytes = self.get_codebytes()
        # print(self.lineotab.hex(" "), "...")
        return CodeType(
            0,  # argcount
            0,  # posonlyargcount
            0,  # kwonlyargcount
            0,  # nlocals
            self.max_stacksize,  # stacksize
            0,  # flags
            codebytes,  # code
            tuple(self.constants),  # consts
            tuple(self.names),  # names
            tuple(self.varnames),  # varnames
            self.filename,  # filename
            self.blockname,  # name
            self.firstlineno,  # firstlineno
            self.lineotab,  # lnotab
            tuple(self.freevars),  # freevars
            tuple(self.cellvars),  # cellvars
        )

if __name__ == '__main__':
    import dis

    def print_opcodes(c: CodeType):
        import opcode
        print(f"co_argcount: {c.co_argcount}")
        print(f"co_posonlyargcount: {c.co_posonlyargcount}")
        print(f"co_kwonlyargcount: {c.co_kwonlyargcount}")
        print(f"co_nlocals: {c.co_nlocals}")
        print(f"co_stacksize: {c.co_stacksize}")
        print(f"co_flags: {c.co_flags}")
        print(f"co_code: {c.co_code}")
        print(f"co_consts: {c.co_consts}")
        print(f"co_names: {c.co_names}")
        print(f"co_varnames: {c.co_varnames}")
        print(f"co_filename: {c.co_filename}")
        print(f"co_name: {c.co_name}")
        print(f"co_firstlineno: {c.co_firstlineno}")
        print(f"co_lnotab: {c.co_lnotab}")
        print(f"co_freevars: {c.co_freevars}")
        print(f"co_cellvars: {c.co_cellvars}")
        print()
        print("co_code ...")
        for i, op in enumerate(c.co_code[::2]):
            print(f"{i * 2} {op:02x} {opcode.opname[op]} :: {c.co_code[2 * i + 1]:02x}")
        print()
        print("co_lnotab ...")
        for i, op in enumerate(c.co_lnotab[::2]):
            print(f"{op:02x} {c.co_lnotab[2 * i + 1]:02x}")
        if len(c.co_lnotab) % 2 == 1:
            print(f"{c.co_lnotab[-1]:02x} ??")

    def a():
        print("a", "b")
        return 3 + 4
    #
    # print_opcodes(a.__code__)
    # dis.dis(a)
    # print(a.__code__.co_lnotab.hex(" "))
    # print(dis.code_info(a.__code__))
    #
    #
    gen = CodeGenerator(filename="test.py").next_line(2)
    gen += "LOAD_GLOBAL", gen.name("print")
    gen += "LOAD_CONST", gen.const("hey")
    gen += "CALL_FUNCTION", 1
    gen += "POP_TOP"
    gen.next_line()
    gen += "LOAD_CONST", gen.const(12)
    gen += "LOAD_CONST", gen.const(13)
    gen += "ROT_TWO"
    gen += "BINARY_TRUE_DIVIDE"
    gen += "LOAD_NAME", gen.name("print")
    gen += "ROT_TWO"
    gen.line = 5
    gen += "CALL_FUNCTION", 1
    gen += "RETURN_VALUE"

    code = gen.build()
    # print(code.co_lnotab.hex(" "))
    # print(*code.co_lines())
    dis.dis(code)

    print_opcodes(code)

    # print(code.co_lnotab)
    # print(dis.code_info(code))
    exec(code)

    # copy = CodeType(
    #     a.__code__.co_argcount,
    #     a.__code__.co_posonlyargcount,
    #     a.__code__.co_kwonlyargcount,
    #     a.__code__.co_nlocals,
    #     a.__code__.co_stacksize,
    #     a.__code__.co_flags,
    #     a.__code__.co_code,
    #     a.__code__.co_consts,
    #     a.__code__.co_names,
    #     a.__code__.co_varnames,
    #     a.__code__.co_filename,
    #     a.__code__.co_name,
    #     a.__code__.co_firstlineno,
    #     bytes.fromhex("0A 00 0F 01"),
    #     a.__code__.co_freevars,
    #     a.__code__.co_cellvars
    # )
    # print_opcodes(copy)
    # print(*copy.co_lines(), "_")
    # dis.dis(copy)
    #
    # print()
    #
    # print(code.co_code, copy.co_code)
    # print(len(code.co_code), len(copy.co_code))
