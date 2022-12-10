from parser._tokens import tokennify


DEFAULTS = dict(
    escape_chars=frozenset(("\\",)),
    majorstruct=None,
)

class Parser:
    def __init__(self, escape_chars=DEFAULTS["escape_chars"], structs=(), majorstruct=None):
        """
        Initialize the parser.
        """
        self.escape_chars = escape_chars
        self.struct_map = {struct.name: struct for struct in structs}
        self.majorstruct = majorstruct

    def __getitem__(self, item):
        if item in DEFAULTS:
            return getattr(self, item)
        raise KeyError(item)

    def __setitem__(self, key, value):
        if key in DEFAULTS:
            setattr(self, key, value)
        else:
            raise KeyError(key)

    def parse(self, string, majorstruct=None):
        majorstruct = majorstruct or self.majorstruct
        if majorstruct is None:
            raise ValueError("No majorstruct specified.")
        lexed = self._lex(string)
        parsed = majorstruct.extract(lexed, self.struct_map)
        return parsed

    def _lex(self, string):
        return tokennify(string, self.escape_chars)

    def add_struct(self, struct):
        if struct.name is not None:
            self.struct_map[struct.name] = struct
        else:
            raise ValueError("Addes structs must have a name.")
