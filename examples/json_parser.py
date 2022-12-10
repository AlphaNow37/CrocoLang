import parser
code = """{
    " a": 1,
    "b": 2,
}"""

blanks = parser.FirstStruct(" ", "\n", "\t") * parser.MINI0
mparser = parser.Parser()
int_struct = parser.Structure(
    (
            parser.Repeat(parser.Char(parser.DIGITS), parser.MINI1, savename="value", kwargs={"type": "int"})+""
     ), "int", parser=mparser)
str_struct = parser.Structure(
    (
            '"'+parser.Repeat(parser.Char(), parser.MINI0, savename="value", kwargs={"type": "str"})+'"'
     ), "str", parser=mparser)
element = parser.Structure(
    (
         int_struct |
         str_struct |
         parser.StructGetter("list") |
         parser.StructGetter("dict")
     ), "element", parser=mparser)
list_element = parser.Structure(parser.SequenceStruct(
        "[",
        parser.Repeat(
            (blanks+parser.StructGetter("element", savename="content")+blanks+","+blanks),
            parser.MINI0,
            savename="value", kwargs={"type": "list"}),
        "]",
    ), "list", parser=mparser)
dict_element = parser.Structure(parser.SequenceStruct(
        "{",
        parser.Repeat(
            (blanks +
             parser.StructGetter("str", savename="key") +
             blanks +
             ":" +
             blanks +
             parser.StructGetter("element", savename="content") +
             blanks +
             "," +
             blanks),
            parser.MINI0,
            savename="value", kwargs={"type": "dict"}),
        "}",
    ), "dict", parser=mparser)

json_struct = element
mparser.majorstruct = json_struct
parsed, used = mparser.parse(code)
assert used == len(code)

def visit_node(node: parser.ast.AST):
    value = node.value
    if value.type == "int":
        return int("".join(value))
    elif value.type == "str":
        return "".join(value)
    elif value.type == "list":
        return [visit_node(e.content) for e in value]
    elif value.type == "dict":
        return {visit_node(e.key): visit_node(e.content) for e in value}

print(visit_node(parsed))
