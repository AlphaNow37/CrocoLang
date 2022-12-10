import code_creator
import pycompile


gen = code_creator.CodeGenerator()
gen += "LOAD_GLOBAL", gen.name("print")
gen += "LOAD_CONST", gen.const("hoooy")
gen += "CALL_FUNCTION", 1
gen += "RETURN_VALUE"
code = gen.build()
pycompile.create_file(
    "new.py",
    code,
    True,
    __file__,
)
import new
