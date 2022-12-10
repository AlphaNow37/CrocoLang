
class CharToken:
    def __init__(self, char, isescaped=False):
        self.char = char
        self.isescaped = isescaped

    def __repr__(self):
        c = "\\"
        return f"CT:{c if self.isescaped else ''}{self.char!r}"

    def __eq__(self, other):
        return isinstance(other, CharToken) and self.char == other.char and self.isescaped == other.isescaped

def tokennify(string, escape_chars):
    tokens: list[CharToken] = []
    i = 0
    while i < len(string):
        char = string[i]
        if char in escape_chars:
            i += 1
            if i == len(string):
                raise Exception("Unexpected end of string with escape character")
            tokens.append(CharToken(string[i], True))
        else:
            tokens.append(CharToken(char))
        i += 1
    return tokens
