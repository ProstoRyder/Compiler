from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PolizStep:
    lexeme: str
    operator_stack: tuple[str, ...]
    output: tuple[str, ...]
    action: str


@dataclass(frozen=True)
class PolizResult:
    poliz: tuple[str, ...]
    steps: tuple[PolizStep, ...]


PRIORITIES = {
    "+": 1,
    "-": 1,
    "*": 2,
    "/": 2,
    "NEG": 3,
    "↑": 4,
}
RIGHT_ASSOCIATIVE = {"↑", "NEG"}
BINARY = {"+", "-", "*", "/", "↑"}


class PolizExpressionError(ValueError):


def convert_expression(
    lexemes: Iterable[object], *, enable_unary_minus: bool = False
) -> PolizResult:
    output: list[str] = []
    stack: list[str] = []
    steps: list[PolizStep] = []
    expecting_operand = True
    seen_any = False

    def trace(lexeme: str, action: str) -> None:
        steps.append(PolizStep(lexeme, tuple(stack), tuple(output), action))

    for raw in lexemes:
        token = raw if isinstance(raw, str) else getattr(raw, "lexeme", None)
        if not isinstance(token, str):
            raise TypeError("Очікується рядок або Token з рядковим полем lexeme")
        seen_any = True

        if token == "(":
            if not expecting_operand:
                raise PolizExpressionError("Перед '(' очікується оператор")
            stack.append(token)
            trace(token, "Дужку додано до стека")
            continue

        if token == ")":
            if expecting_operand:
                raise PolizExpressionError("Перед ')' очікується операнд")
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise PolizExpressionError("Зайва закривальна дужка")
            stack.pop()
            trace(token, "Витягнуто оператори до відкривальної дужки")
            expecting_operand = False
            continue

        if token in BINARY:
            if token == "-" and expecting_operand:
                if not enable_unary_minus:
                    raise PolizExpressionError(
                        "Унарний мінус не входить до граматики варіанта №4"
                    )
                stack.append("NEG")
                trace(token, "Унарний '-' замінено спеціальною операцією NEG")
                continue

            if expecting_operand:
                raise PolizExpressionError(f"Перед '{token}' очікується операнд")

            while stack and stack[-1] in PRIORITIES:
                top = stack[-1]
                if (
                    PRIORITIES[top] > PRIORITIES[token]
                    or (
                        PRIORITIES[top] == PRIORITIES[token]
                        and token not in RIGHT_ASSOCIATIVE
                    )
                ):
                    output.append(stack.pop())
                else:
                    break
            stack.append(token)
            trace(token, "Оператор додано до стека з урахуванням пріоритету")
            expecting_operand = True
            continue

        if not (token.isidentifier() or token.isdecimal()):
            raise PolizExpressionError(f"Недопустима лексема у виразі: {token!r}")
        if not expecting_operand:
            raise PolizExpressionError(f"Перед '{token}' очікується оператор")
        output.append(token)
        trace(token, "Операнд додано до вихідного ПОЛІЗ")
        expecting_operand = False

    if not seen_any or expecting_operand:
        raise PolizExpressionError("Арифметичний вираз незавершений або порожній")

    while stack:
        op = stack.pop()
        if op == "(":
            raise PolizExpressionError("Незакрита дужка у виразі")
        output.append(op)
    trace("кінець виразу", "Вивантажено залишок стека операторів")
    return PolizResult(tuple(output), tuple(steps))


if __name__ == "__main__":
    result = convert_expression("( sum + 2 ) * 3 - 8 / 2 + 2 ↑ 3".split())
    for idx, step in enumerate(result.steps, 1):
        print(
            f"{idx:2}. {step.lexeme:<14} | "
            f"{(' '.join(step.operator_stack) or '∅'):<16} | "
            f"{' '.join(step.output)}"
        )
    print("ПОЛІЗ:", " ".join(result.poliz))
