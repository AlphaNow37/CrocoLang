from functools import total_ordering


@total_ordering
class Indexer:
    shrort_repr = False

    def __init__(self, code: str, index=0, line=0, column=1):
        if code.__class__.__name__ != "CharStream":
            raise
        self.code = code
        self.i = index
        self.line = line
        self.column = column

    def _add(self, i):
        new_i = self.i + i
        new_line = self.line + self.code[self.i:new_i].count('\n')
        new_column = (self.column + i) if new_line == self.line else (new_i - self.code.rfind('\n', 0, new_i+1))
        return new_i, new_line, new_column

    def __add__(self, other):
        return Indexer(self.code, *self._add(other))

    def __iadd__(self, other):
        self.i, self.line, self.column = self._add(other)
        return self

    def __gt__(self, other):
        return self.i > getattr(other, 'i', other)

    def __eq__(self, other):
        return self.i == getattr(other, 'i', other)

    def __index__(self):
        return self.i

    def get_token(self, length):
        return Token(
            self.line,
            self.column,
            self.i,
            self.code,
            length,
            short_repr=self.shrort_repr
        )

    def __repr__(self):
        return f"Indexer({self.i}, {self.line}, {self.column})"

class Token(str):
    def __new__(cls, start_line: int, start_column: int, offset: int, code: str, length: int, *, short_repr=False):
        frag = code[offset:offset + length]
        end_line = start_line + frag.count('\n')
        end_column = start_column + length if end_line == start_line else length - frag.rfind('\n')
        end_offset = offset + length
        self = super().__new__(cls, frag)
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column
        self.offset = offset
        self.end_offset = end_offset

        self.short_repr = short_repr
        return self

    def __repr__(self):
        if self.short_repr:
            return super().__repr__()
        return f"Token({self.start_line}, {self.start_column}, {self.offset}, {super().__repr__()}, {len(self)})"


# code = """
# ABC
# DEF
# GHI
# """
# print(repr(Token(1, 1, 2, code, 3)))
