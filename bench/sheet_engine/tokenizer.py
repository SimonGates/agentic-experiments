from __future__ import annotations

from dataclasses import dataclass


class TokenError(Exception):
    pass


@dataclass(frozen=True)
class Token:
    type: str
    value: object
    pos: int


_TWO_CHAR = {
    "<>": "NE",
    "<=": "LE",
    ">=": "GE",
}

_ONE_CHAR = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "&": "AMP",
    "=": "EQ",
    "<": "LT",
    ">": "GT",
    "(": "LPAREN",
    ")": "RPAREN",
    ",": "COMMA",
    ":": "COLON",
}


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and text[i + 1].isdigit()):
            tok, i = _read_number(text, i)
            tokens.append(tok)
            continue
        if ch == '"':
            tok, i = _read_string(text, i)
            tokens.append(tok)
            continue
        if ch.isalpha() or ch == "_":
            tok, i = _read_ident_or_cell(text, i)
            tokens.append(tok)
            continue
        if i + 1 < n and text[i : i + 2] in _TWO_CHAR:
            tokens.append(Token(_TWO_CHAR[text[i : i + 2]], text[i : i + 2], i))
            i += 2
            continue
        if ch in _ONE_CHAR:
            tokens.append(Token(_ONE_CHAR[ch], ch, i))
            i += 1
            continue
        raise TokenError(f"unexpected character {ch!r} at {i}")
    tokens.append(Token("EOF", None, n))
    return tokens


def _read_number(text: str, i: int) -> tuple[Token, int]:
    start = i
    n = len(text)
    if text[i] == ".":
        i += 1
        while i < n and text[i].isdigit():
            i += 1
    else:
        while i < n and text[i].isdigit():
            i += 1
        if i < n and text[i] == ".":
            i += 1
            while i < n and text[i].isdigit():
                i += 1
    raw = text[start:i]
    if "." in raw:
        value: int | float = float(raw)
    else:
        value = int(raw)
    return Token("NUMBER", value, start), i


def _read_string(text: str, i: int) -> tuple[Token, int]:
    start = i
    i += 1
    n = len(text)
    chars: list[str] = []
    while i < n:
        if text[i] == '"':
            if i + 1 < n and text[i + 1] == '"':
                chars.append('"')
                i += 2
                continue
            i += 1
            return Token("STRING", "".join(chars), start), i
        chars.append(text[i])
        i += 1
    raise TokenError("unterminated string")


def _read_ident_or_cell(text: str, i: int) -> tuple[Token, int]:
    start = i
    n = len(text)
    i += 1
    while i < n and (text[i].isalnum() or text[i] == "_"):
        i += 1
    raw = text[start:i]
    if len(raw) >= 2 and raw[0].isalpha() and raw[1:].isdigit():
        return Token("CELL", raw.upper(), start), i
    return Token("IDENT", raw, start), i
