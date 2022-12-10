from textwrap import indent as indenter


class AST:
    def __init__(self, **attrs):
        self.attrs = attrs

    def __getattr__(self, item):
        value = self.attrs.get(item)
        if value is None:
            raise AttributeError(item)
        return value

    def __getitem__(self, item):
        return self.attrs[item]

    def __repr__(self, indent=4):
        line_change = "\n" if indent is not None else ""
        indent_add = " " * indent if indent is not None else ""
        cls_name = self.__class__.__name__ + "(" + line_change
        middle = ""
        for key, value in self.attrs.items():
            if key == "__items__":
                assert isinstance(value, list)
                value = f"[{line_change}{indenter(line_change.join(map(repr, value)), indent_add)}{line_change}]"
            else:
                value = repr(value)
            text = f'{key}={value}'
            middle += indenter(text, indent_add) + ", " + line_change
        return f"{cls_name}{middle})"

class List(AST):
    def __init__(self, items, **attrs):
        super(List, self).__init__(**attrs, __items__=items)

    def __iter__(self):
        return iter(self.__items__)
