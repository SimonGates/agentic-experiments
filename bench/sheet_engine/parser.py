from __future__ import annotations

from sheet_engine.ast import (
    BinaryOp,
    Boolean,
    CellRef,
    Expr,
    FunctionCall,
    Number,
    Range,
    String,
    UnaryOp,
)
from sheet_engine.tokenizer import Token, TokenError, tokenize


class ParseError(Exception):
    pass


def parse_formula(text: str) -> Expr:
    if not text.startswith("="):
        raise ParseError("not a formula")
    try:
        tokens = tokenize(text[1:])
    except TokenError as exc:
        raise ParseError(str(exc)) from exc
    return Parser(tokens).parse()


def parse_cell_addr(addr: str) -> CellRef | None:
    if not addr:
        return None
    addr = addr.strip().upper()
    i = 0
    if i >= len(addr) or not addr[i].isalpha():
        return None
    col = addr[i]
    i += 1
    if i >= len(addr) or not addr[i].isdigit():
        return None
    row_s = addr[i:]
    if not row_s.isdigit():
        return None
    ref = CellRef(col, int(row_s))
    if not ref.valid:
        return None
    return ref


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.i = 0

    def parse(self) -> Expr:
        expr = self._comparison()
        self._expect("EOF")
        return expr

    @property
    def _tok(self) -> Token:
        return self.tokens[self.i]

    def _eat(self, typ: str) -> Token:
        tok = self._tok
        if tok.type != typ:
            raise ParseError(f"expected {typ}, got {tok.type}")
        self.i += 1
        return tok

    def _expect(self, typ: str) -> Token:
        return self._eat(typ)

    def _match(self, *types: str) -> Token | None:
        if self._tok.type in types:
            tok = self._tok
            self.i += 1
            return tok
        return None

    def _comparison(self) -> Expr:
        left = self._concat()
        tok = self._match("EQ", "NE", "GT", "GE", "LT", "LE")
        if tok is None:
            return left
        right = self._concat()
        return BinaryOp(str(tok.value), left, right)

    def _concat(self) -> Expr:
        left = self._arith()
        while True:
            tok = self._match("AMP")
            if tok is None:
                return left
            right = self._arith()
            left = BinaryOp("&", left, right)

    def _arith(self) -> Expr:
        left = self._term()
        while True:
            tok = self._match("PLUS", "MINUS")
            if tok is None:
                return left
            right = self._term()
            left = BinaryOp(str(tok.value), left, right)

    def _term(self) -> Expr:
        left = self._unary()
        while True:
            tok = self._match("STAR", "SLASH")
            if tok is None:
                return left
            right = self._unary()
            left = BinaryOp(str(tok.value), left, right)

    def _unary(self) -> Expr:
        tok = self._match("MINUS")
        if tok is not None:
            return UnaryOp("-", self._unary())
        return self._primary()

    def _primary(self) -> Expr:
        tok = self._tok
        if tok.type == "NUMBER":
            self.i += 1
            val = tok.value
            assert isinstance(val, (int, float))
            return Number(val)
        if tok.type == "STRING":
            self.i += 1
            return String(str(tok.value))
        if tok.type == "CELL":
            self.i += 1
            start = _cell_from_token(str(tok.value))
            if self._match("COLON"):
                end_tok = self._eat("CELL")
                end = _cell_from_token(str(end_tok.value))
                return Range(start, end)
            return start
        if tok.type == "IDENT":
            self.i += 1
            name = str(tok.value)
            if self._match("LPAREN"):
                args = self._args()
                self._eat("RPAREN")
                return FunctionCall(name.upper(), tuple(args))
            upper = name.upper()
            if upper == "TRUE":
                return Boolean(True)
            if upper == "FALSE":
                return Boolean(False)
            raise ParseError(f"unexpected identifier {name}")
        if tok.type == "LPAREN":
            self.i += 1
            expr = self._comparison()
            self._eat("RPAREN")
            return expr
        raise ParseError(f"unexpected token {tok.type}")

    def _args(self) -> list[Expr]:
        if self._tok.type == "RPAREN":
            return []
        args = [self._comparison()]
        while self._match("COMMA"):
            args.append(self._comparison())
        return args


def _cell_from_token(raw: str) -> CellRef:
    col = raw[0]
    row = int(raw[1:])
    return CellRef(col, row)
