from parser_v2 import var
from parser_v2.token import Indexer

def _get(val, namespace):
    if isinstance(val, var.Partial):
        return val.get(namespace)
    return val


DBG_MODE = False

class BasicStruct:
    factory = None

    def __set_name__(self, owner, name):
        self.name = name

    def __init__(self, factory=None):
        self.name = None
        if factory is not None:
            self.factory = factory

    def set_factory(self, factory):
        if factory is not None:
            self.factory = factory
        return self

    def _parse(self, namespace, index: "Indexer", code) -> (object | None, int):
        raise NotImplementedError

    def _getargs(self, obj):
        return [obj]

    def parse(self, namespace, index: "Indexer", code) -> (object | None, int):
        if DBG_MODE:
            print(f"Parsing by {self.name if self.name else '?'}={self} started from {index}")
        obj, index = self._parse(namespace, index, code)
        if obj is not None and self.factory is not None:
            obj = self.factory(*self._getargs(obj))
        return obj, index

    def expect(self, message, etype=SyntaxError):
        return Expected(self, message, etype=etype)

    def __add__(self, other):
        return Seq(self, other)

    def __radd__(self, other):
        return Seq(other, self)

    def __or__(self, other):
        return Any(self, other)

    def __mul__(self, other):
        if isinstance(other, tuple):
            return Repeat(self, *other)
        return Repeat(self, other, other)

    def __invert__(self):
        return Not(self)

    def __repr__(self):
        if self.name:
            return self.name
        elif hasattr(self, "__str__"):
            return str(self)
        else:
            return super().__repr__()

class Str(BasicStruct):
    def __init__(self, value, factory=None):
        self.value = value
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        string = _get(self.value, namespace)
        if not isinstance(string, str):
            raise TypeError(f"Expected str, got {type(string)}")
        if code.startswith(string, index):
            tok = index.get_token(len(string))
            return tok, index + len(string)
        return None, index

    def __str__(self):
        return f"{self.name or 'Str'}({self.value!r})"

class Finalisable(BasicStruct):
    def __init__(self, factory):
        super().__init__(factory)
        self.is_final = False

    def final(self):
        self.is_final = True
        return self

    def set_factory(self, factory):
        self.is_final = True
        return super().set_factory(factory)

class Any(Finalisable):
    def __init__(self, *values, factory=None):
        self.values = [_convert(value) for value in values]
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        for value in self.values:
            value, idx = value.parse(namespace, index, code)
            if value is not None:
                return value, idx
        return None, index

    def __or__(self, other):
        if self.is_final:
            return super().__or__(other)
        return Any(*self.values, other)

    def __str__(self):
        return f"{self.name or 'Any'}({', '.join(map(repr, self.values))})"


class Sequence(Finalisable):
    factory = tuple
    indexes = [slice(None, None, None)]

    def __init__(self, *values, factory=None, indexes=None):
        super().__init__(factory=factory)
        self.values = [_convert(value) for value in values]
        self.is_final = factory is not None
        if indexes is not None:
            self.indexes = indexes

    def _getargs(self, obj):
        return [obj[i] for i in self.indexes]

    def _parse(self, namespace, index, code) -> (object | None, int):
        before_idx = index
        values = []
        for value in self.values:
            value, index = value.parse(namespace, index, code)
            if value is None:
                return None, before_idx
            values.append(value)
        return values, index

    def __add__(self, other):
        if self.is_final:
            return Seq(self, other)
        return Sequence(*self.values, other)

    def set_factory(self, factory, indexes=None):
        if indexes is not None:
            self.indexes = indexes
        return super().set_factory(factory)

    def set_indexes(self, indexes):
        return self.set_factory(None, indexes)

    def __str__(self):
        return f"{self.name or 'Seq'}({', '.join(map(repr, self.values))})"

Seq = Sequence

class Repeat(BasicStruct):
    factory = list
    pass_joiners = False

    def __init__(self, struct, mini=0, maxi=None, join=None, factory=None):
        self.struct = _convert(struct)
        self.mini = mini
        self.maxi = maxi
        self.join = _convert(join) if join is not None else None
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        mini = _get(self.mini, namespace)
        # print(mini, self.mini, namespace)
        maxi = _get(self.maxi, namespace)
        if maxi == 0:
            return ([], []), index
        values = []
        joins = []
        first = True
        original_index = index
        while True:
            last_index = index
            if not first and self.join is not None:
                join, index = self.join.parse(namespace, index, code)
                if join is None:
                    break
                joins.append(join)
            value, index = self.struct.parse(namespace, index, code)
            if value is None:
                index = last_index
                break
            values.append(value)
            if maxi is not None and len(values) >= maxi:
                break
            first = False
            if index == last_index and self.maxi is None:
                break
        if len(values) < mini:
            return None, original_index
        return (values, joins), index

    def _getargs(self, obj):
        if self.pass_joiners:
            return obj
        return [obj[0]]

    def set_factory(self, factory, pass_joiners=False):
        self.pass_joiners = pass_joiners
        return super().set_factory(factory)

    def __str__(self):
        s = f"{self.name or 'Repeat'}({self.struct!r}"
        if self.mini != 0:
            s += f", mini={self.mini}"
        if self.maxi is not None:
            s += f", maxi={self.maxi}"
        if self.join is not None:
            s += f", join={self.join!r}"
        return s + ")"

class Expected(BasicStruct):
    def __init__(self, struct, message, factory=None, etype=SyntaxError):
        self.struct = _convert(struct)
        self.message = message
        self.etype = etype
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        value, index = self.struct.parse(namespace, index, code)
        if value is None:
            e = self.etype(self.message.format(i=index, code=code, ns=namespace, line=index.line+1, col=index.column))
            e.lineno = index.line + 1
            # e.offset = index.column
            # e.end_offset = -1
            # e.end_lineno = index.line + 1
            raise e
        return value, index

    def __str__(self):
        return f"{self.name or '!'}({self.struct!r})"

class Not(BasicStruct):
    def __init__(self, struct, factory=None, increment=1):
        self.struct = _convert(struct)
        self.increment = increment
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        value, _ = self.struct.parse(namespace, index, code)
        right = index + self.increment
        if value is None and right <= len(code):
            if self.increment == 0:
                return "", index
            return index.get_token(self.increment), right
        return None, index

    def __str__(self):
        return f"{self.name or '~'}({self.struct!r})"

class UpdateNameSpace(BasicStruct):
    def __init__(self, struct, ns=None, /, **ns_):
        self.struct = _convert(struct)
        self.ns = (ns or {}) | ns_
        super().__init__()

    def _parse(self, lnamespace, index, code) -> (object | None, int):
        namespace = lnamespace | {key: _get(val, lnamespace) for (key, val) in self.ns.items()}
        return self.struct.parse(namespace, index, code)

    def __str__(self):
        return f"{self.name or 'UNS'}({self.struct!r}, {self.ns})"

UNS = UpdateNameSpace

class SaveAs(BasicStruct):
    def __init__(self, struct, name, factory=None):
        self.struct = _convert(struct)
        self.vname = name
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        value, index = self.struct.parse(namespace, index, code)
        if value is not None:
            namespace[self.vname] = value
        return value, index

    def __str__(self):
        return f"{self.name or 'SaveAs'}({self.struct!r}, {self.vname!r})"

class End(BasicStruct):
    def _parse(self, namespace, index, code) -> (object | None, int):
        if index == len(code):
            return True, index
        return None, index

    def __str__(self):
        return f"{self.name or 'END'}"

END = End()

def _convert(value) -> BasicStruct:
    if isinstance(value, BasicStruct):
        return value
    elif isinstance(value, str):
        return Str(value)
    raise TypeError(f"Expected str or BasicStruct, got {type(value)}")
