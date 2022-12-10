from parser._tokens import CharToken
from parser import ast

class BasicStruct:
    savename = None

    def extract(self, tokens: list[CharToken], struct_map) -> tuple[..., int]:
        """
        Extracts the structure from the tokens.
        :param tokens: A list of CharTokens that represent all the data that wasn't parsed yet.
        :param struct_map: a dict[name: Struct] that contains all the structures that are usable by name.
        :return: an ast/other if the extraction was successful, None if it wasn't.
        :return: the number of tokens that were used to extract the structure.
        """
        raise NotImplementedError

    def __add__(self, other):
        return SequenceStruct(self, cast_interface(other))

    def __radd__(self, other):
        return SequenceStruct(cast_interface(other), self)

    def __or__(self, other):
        return FirstStruct(self, cast_interface(other))

    def __ror__(self, other):
        return FirstStruct(cast_interface(other), self)

    def __mul__(self, other):
        return Repeat(self, other)
    __rmul__ = __mul__

class Structure(BasicStruct):
    def __init__(self, data: BasicStruct | str, name=None, *, parser=None, savename=None):
        self.name = name
        if parser and name not in parser.struct_map:
            parser.add_struct(self)
        data = cast_interface(data)
        if isinstance(data, Structure):
            self.data = data.data
        else:
            self.data = data
        self.savename = savename

    def extract(self, tokens: list[CharToken], struct_map):
        return self.data.extract(tokens, struct_map)


class String(BasicStruct):
    def __init__(self, string: str):
        self.string = string

    def extract(self, tokens: list[CharToken], struct_map):
        if len(tokens) < len(self.string):
            return None, 0
        if all(tokens[i].char == char for i, char in enumerate(self.string)):
            return self.string, len(self.string)
        return None, 0

class Char(BasicStruct):
    def __init__(self, char: str | set[str], excluded=False, noescape=False):
        self.chars = set(char)
        self.excluded = excluded
        self.noescape = noescape

    def extract(self, tokens: list[CharToken], struct_map):
        if len(tokens) < 1:
            return None, 0
        token = tokens[0]
        contained = token.char in self.chars
        excluded = self.excluded
        escaping = (self.noescape and token.isescaped) ^ excluded

        match (contained, escaping, excluded):
            case (True, False, False) | (False, False, True):
                return token.char, 1
            case (False, _, False):
                return None, 0

        if tokens[0].char in self.chars:
            if self.excluded:
                if self.noescape and token.isescaped:
                    return token.char, 1
                else:
                    return None, 0
            elif self.noescape and token.isescaped:
                return None, 0
            else:
                return token.char, 1
        else:
            if self.excluded:
                return token.char, 1
            else:
                return None, 0

class SequenceStruct(BasicStruct):
    def __init__(self, *parts: BasicStruct | str, savename=None, sep=None):
        self.savename = savename
        self.parts = []
        if sep is None:
            self.sep = None
        elif isinstance(sep, list | set | tuple):
            self.sep = FirstStruct(*sep)
        else:
            self.sep = cast_interface(sep)
        for part in parts:
            if isinstance(part, SequenceStruct):
                self.parts.extend(part.parts)
            else:
                self.parts.append(cast_interface(part))

    def extract(self, tokens: list[CharToken], struct_map):
        kws = {}
        i = 0
        for part in self.parts:
            if self.sep is not None:
                while True:
                    res, sep_used = self.sep.extract(tokens[i:], struct_map)
                    if res is not None:
                        i += sep_used
                    else:
                        break
            extracted_data, used = part.extract(tokens[i:], struct_map)
            if extracted_data is None:
                return None, 0
            i += used
            if savename := getattr(part, "savename", None):
                kws[savename] = extracted_data
        return ast.AST(**kws), i

class FirstStruct(BasicStruct):
    def __init__(self, *parts: BasicStruct | str, savename=None):
        self.savename = savename
        self.parts = [cast_interface(part) for part in parts]

    def extract(self, tokens: list[CharToken], struct_map):
        for part in self.parts:
            extracted, used = part.extract(tokens, struct_map)
            if extracted is not None:
                return extracted, used
        return None, 0

class StructGetter(BasicStruct):
    def __init__(self, name: str, savename=None):
        self.savename = savename
        self.name = name

    def extract(self, tokens: list[CharToken], struct_map):
        return struct_map[self.name].extract(tokens, struct_map)

class Repeat(BasicStruct):
    def __init__(self, data: BasicStruct, mini, maxi=None, *, savename=None, kwargs=None):
        self.kwargs = kwargs or {}
        self.data = data
        self.savename = savename

        if maxi is None:
            if isinstance(mini, _RepeatConst):
                mini = mini.count
            if isinstance(mini, int):
                maxi = mini
            else:
                mini, maxi = mini
        self.mini = mini
        self.maxi = maxi

    def extract(self, tokens: list[CharToken], struct_map):
        extracted = []
        i = 0
        for _ in range(self.mini):
            extracted_data, used = self.data.extract(tokens[i:], struct_map)
            if extracted_data is None:
                return None, 0
            i += used
            extracted.append(extracted_data)
        n = 0
        while n < self.maxi - self.mini:
            extracted_data, used = self.data.extract(tokens[i:], struct_map)
            if extracted_data is None:
                break
            i += used
            extracted.append(extracted_data)
            n += 1
        return ast.List(extracted, **self.kwargs), i


class _RepeatConst:
    def __init__(self, count):
        self.count = count

    def __mul__(self, other):
        return Repeat(other, self.count)
    __rmul__ = __mul__

MINI0 = _RepeatConst((0, float('inf')))
MINI1 = _RepeatConst((1, float('inf')))

def cast_interface(interface) -> BasicStruct:
    if isinstance(interface, str):
        return String(interface)
    elif isinstance(interface, BasicStruct):
        return interface
    else:
        raise TypeError("Interface must be a string or a StructInterface")

def saved_as(struct, savename):
    return Structure(struct, savename=savename)
