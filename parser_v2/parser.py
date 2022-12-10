
from parser_v2.struct import BasicStruct
from parser_v2.token import Indexer


class Parser:
    __start__: str = "start"

    def __init_subclass__(cls, start=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__start__ = start or cls.__start__

    def __new__(cls, code, start=None, index=0, /, **namespace):
        return cls._parse(code, start=start, namespace=namespace, index=index)

    @classmethod
    def _parse(cls, code, start=None, namespace=None, index=0):
        namespace = vars(cls) | (namespace or {})
        start = start or cls.__start__
        if isinstance(start, str):
            starter = getattr(cls, start)
        elif isinstance(start, BasicStruct):
            starter = start
        else:
            raise TypeError(f"{start} is not a valid start")
        if isinstance(index, int):
            index = Indexer(code) + index
        obj, index = starter.parse(namespace, index, code)
        if index != len(code):
            raise SyntaxError(f"Unexpected token {code[index]!r}")
        return obj

    parse = _parse

def parse(parser, code, start=None, namespace=None, index=0, /, **ns):
    if not issubclass(parser, Parser):
        raise TypeError("Parser must be a subclass of Parser")
    return parser.parse(code, start=start, namespace=namespace | ns, index=index)

if __name__ == '__main__':
    class A(Parser):
        a = 1
        b = 2

