
class CharStream:
    """
    A stream of characters.
    Used for interactive mode.
    Compatible with the parser.
    """
    def __init__(self, ask_input):
        self.ask_input = ask_input
        self.buffer = ""
        self.stop = False

    def _get(self, i):
        while i >= len(self.buffer):
            if self.stop:
                return ""
            input_value = self.ask_input()
            if input_value is None:
                self.stop = True
                return ""
            self.buffer += input_value
        return self.buffer[i]

    def __getitem__(self, i):
        if isinstance(i, slice):
            return "".join(self._get(j) for j in range(*i.indices(len(self.buffer))))
        return self._get(i)

    def __len__(self):
        return len(self.buffer)

    def __repr__(self):
        return f"CharStream({self.buffer!r})"

    def rfind(self, char, start, end):  # Used by token.Indexer
        self._get(end)
        return self.buffer.rfind(char, start, end)

    def startswith(self, string, start):
        for i, char in enumerate(string):
            if self._get(start + i) != char:
                return False
        return True

    def split(self, *args, **kwargs):
        return self.buffer.split(*args, **kwargs)

if __name__ == '__main__':
    from parser_v2.parser import Parser
    from parser_v2.struct import Repeat, Not, Str, Any, END

    # class A(Parser):
    #     end = Str("f")
    #     before = Repeat(Not(end))
    #     __start__ = before + end
    #
    # i = 0
    # def ask_input():
    #     global i
    #     i += 1
    #     return chr(ord("a") + i - 1)
    #
    # print(A(CharStream(ask_input)))

    # class B(Parser):
    #     whites = Repeat(Any(*" \t\n\r"))
    #     __start__ = whites + "(" + whites + ")"
    #
    # lines = [
    #     "    (    ",
    #     "    ",
    #     "    )",
    #     "__must_fail__",
    # ]
    # i = 0
    # def ask_input():
    #     global i
    #     i += 1
    #     return lines[i - 1]
    #
    # print(B(CharStream(ask_input)))

    class C(Parser):
        line = Repeat(Not(Str("\n")))
        lines = Repeat(line, join="\n") + END
        __start__ = lines

    lines = iter([
        "line1\n",
        "line2",
    ])

    def ask_input():
        try:
            return next(lines)
        except StopIteration:
            return None

    print(C(CharStream(ask_input)))
