
from parser_v2.struct import BasicStruct
from parser_v2.token import Indexer

import code

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
            e = SyntaxError(f"Unexpected token {code[index]!r}, line {index.line}, column {index.column}")
            e.lineno = index.line + 1
            raise e
        return obj

    parse = _parse

def parse(parser, code, start=None, namespace=None, index=0, /, **ns):
    if not issubclass(parser, Parser):
        raise TypeError("Parser must be a subclass of Parser")
    return parser.parse(code, start=start, namespace=(namespace or {}) | ns, index=index)

def parse_file(parser, path, start=None, namespace=None, index=0, /, **ns):
    with open(path) as f:
        content = f.read()
        try:
            return parse(parser, content, start=start, namespace=(namespace or {}) | ns, index=index)
        except SyntaxError as e:
            e.filename = path
            e.text = content.split("\n")[e.lineno - 1]
            raise

if __name__ == '__main__':
    class A(Parser):
        a = 1
        b = 2

