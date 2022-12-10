from parser_v2 import var
from parser_v2.token import Indexer

def _get(val, namespace):
    if isinstance(val, var.Partial):
        return val.get(namespace)
    return val

class BasicStruct:
    factory = None

    def __init__(self, factory=None):
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
        obj, index = self._parse(namespace, index, code)
        if obj is not None and self.factory is not None:
            obj = self.factory(*self._getargs(obj))
        return obj, index

    def expect(self, message):
        return Expected(self, message)

    def __add__(self, other):
        return Seq(self, other)

    def __or__(self, other):
        return Any(self, other)

    def __mul__(self, other):
        if isinstance(other, tuple):
            return Repeat(self, *other)
        return Repeat(self, other, other)

    def __invert__(self):
        return Not(self)


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

class Any(BasicStruct):
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
        return Any(*self.values, other)


class Sequence(BasicStruct):
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
        self.is_final = True
        if indexes is not None:
            self.indexes = indexes
        return super().set_factory(factory)

    def set_indexes(self, indexes):
        return self.set_factory(None, indexes)

    def final(self):
        self.is_final = True
        return self

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
        while True:
            last_index = index
            if not first and self.join is not None:
                join, index = self.join.parse(namespace, index, code)
                if join is None:
                    break
                joins.append(join)
            value, index = self.struct.parse(namespace, index, code)
            if value is None:
                break
            values.append(value)
            if maxi is not None and len(values) >= maxi:
                break
            first = False
            if index == last_index:
                break
        if len(values) < mini:
            return None, index
        return (values, joins), index

    def _getargs(self, obj):
        if self.pass_joiners:
            return obj
        return [obj[0]]

    def set_factory(self, factory, pass_joiners=False):
        self.pass_joiners = pass_joiners
        return super().set_factory(factory)

class Expected(BasicStruct):
    def __init__(self, struct, message, factory=None):
        self.struct = _convert(struct)
        self.message = message
        super().__init__(factory)

    def __repr__(self):
        return f"Expected({self.struct!r}, {self.message!r})"

    def _parse(self, namespace, index, code) -> (object | None, int):
        value, index = self.struct.parse(namespace, index, code)
        if value is None:
            print(repr(code[index.i:]))
            raise SyntaxError(self.message.format(i=index, code=code, ns=namespace))
        return value, index

class Not(BasicStruct):
    def __init__(self, struct, factory=None, increment=1):
        self.struct = _convert(struct)
        self.increment = increment
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        value, _ = self.struct.parse(namespace, index, code)
        if value is None and index+self.increment <= len(code):
            if self.increment == 0:
                return "", index
            return index.get_token(self.increment), index+self.increment
        return None, index

class UpdateNameSpace(BasicStruct):
    def __init__(self, struct, ns=None, /, **ns_):
        self.struct = _convert(struct)
        self.ns = (ns or {}) | ns_
        super().__init__()

    def _parse(self, namespace, index, code) -> (object | None, int):
        namespace = namespace | {key: _get(val, namespace) for (key, val) in self.ns.items()}
        return self.struct.parse(namespace, index, code)

UNS = UpdateNameSpace

class SaveAs(BasicStruct):
    def __init__(self, struct, name, factory=None):
        self.struct = _convert(struct)
        self.name = name
        super().__init__(factory)

    def _parse(self, namespace, index, code) -> (object | None, int):
        value, index = self.struct.parse(namespace, index, code)
        if value is not None:
            namespace[self.name] = value
        return value, index

class End(BasicStruct):
    def _parse(self, namespace, index, code) -> (object | None, int):
        if index == len(code):
            return True, index
        return None, index

END = End()

def _convert(value) -> BasicStruct:
    if isinstance(value, BasicStruct):
        return value
    elif isinstance(value, str):
        return Str(value)
    raise TypeError(f"Expected str or BasicStruct, got {type(value)}")
