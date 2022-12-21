from parser_v2.struct import BasicStruct, _get


class Partial(BasicStruct):
    def get(self, namespace):
        raise NotImplementedError

    def add(self, other):
        return Transformer(lambda ns: self.get(ns) + _get(other, ns))

    def mul(self, other):
        return Transformer(lambda ns: self.get(ns) * _get(other, ns))

    def ifelse(self, true, false):
        return Transformer(lambda ns: _get(true, ns) if self.get(ns) else _get(false, ns))

    def _parse(self, namespace, index, code) -> (object | None, int):
        value = self.get(namespace)
        if isinstance(value, BasicStruct):
            return value.parse(namespace, index, code)
        elif isinstance(value, str):
            if code.startswith(value, index):
                return index.get_token(len(value)), index + len(value)
            else:
                return None, index
        raise TypeError(f"Value of {self} cannot be used to parse")

class Transformer(Partial):
    def __init__(self, transform):
        self.transform = transform
        super(Transformer, self).__init__()

    def __str__(self):
        return f"{self.name or 'Transformer'}({self.transform!r})"

    def get(self, namespace):
        return self.transform(namespace)

class Var(Partial):
    def __init__(self, name):
        self.vname = name
        super(Var, self).__init__()

    def __str__(self):
        return f"{self.name or 'Var'}({self.vname})"

    def get(self, namespace):
        try:
            return namespace[self.vname]
        except KeyError:
            raise NameError(f"{self} : Variable {self.vname} not found")

if __name__ == '__main__':
    p = (Var("a") + 1) * 2
    print(p.get({"a": 1}))
