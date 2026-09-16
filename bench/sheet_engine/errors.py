class SheetError(Exception):
    code = "#ERROR!"


class DivZeroError(SheetError):
    code = "#DIV/0!"


class CycleError(SheetError):
    code = "#CYCLE!"


class ErrorValue:
    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ErrorValue) and self.code == other.code

    def __repr__(self) -> str:
        return f"ErrorValue({self.code!r})"


DIVZERO = ErrorValue("#DIV/0!")
ERROR = ErrorValue("#ERROR!")
CYCLE = ErrorValue("#CYCLE!")
