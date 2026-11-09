from __future__ import annotations

from dataclasses import dataclass, field

from tokens import (
    KEYWORDS, SINGLE_CHAR_TOKENS, DOUBLE_CHAR_TOKENS,
    END_PROGRAM, NEWLINE, IDENTIFIER, CONSTANT,
)


@dataclass(frozen=True)
class Token:
    lexeme: str
    code: int
    line: int
    index: int | None = None


@dataclass(frozen=True)
class TraceStep:

    number: int
    state: str
    next_state: str
    symbol: str
    line: int
    column: int
    buffer: str
    action: str
    start: int
    end: int
    token_count: int
    idn_count: int
    con_count: int


@dataclass
class LexerResult:
    tokens: list[Token]
    idn: list[str]
    con: list[str]
    steps: list[TraceStep] = field(default_factory=list)


class LexicalError(Exception):
    def __init__(
        self,
        line: int,
        message: str,
        *,
        column: int = 1,
        start: int = 0,
        end: int = 1,
        partial_result: LexerResult | None = None,
    ):
        self.line = line
        self.column = column
        self.start = start
        self.end = end
        self.partial_result = partial_result
        super().__init__(f"Рядок {line}, позиція {column}: {message}")


class Lexer:
    def scan(self, source: str, *, trace: bool = False) -> LexerResult:
        text = source.replace("\r\n", "\n").replace("\r", "\n")
        tokens: list[Token] = []
        idn: list[str] = []
        con: list[str] = []
        idn_indices: dict[str, int] = {}
        con_indices: dict[str, int] = {}
        steps: list[TraceStep] = []

        i = 0
        token_start = 0
        line = 1
        line_start = 0
        state = "S0"
        lexeme = ""
        code = 0
        index: int | None = None

        def column_at(position: int) -> int:
            return position - (text.rfind("\n", 0, position) + 1) + 1

        def record(
            previous: str,
            next_state: str,
            action: str,
            symbol: str,
            start: int,
            end: int,
        ) -> None:
            if trace:
                start = max(0, min(start, len(text)))
                end = max(start, min(end, len(text)))
                steps.append(TraceStep(
                    number=len(steps) + 1,
                    state=previous,
                    next_state=next_state,
                    symbol=symbol,
                    line=text.count("\n", 0, start) + 1,
                    column=column_at(start),
                    buffer=lexeme,
                    action=action,
                    start=start,
                    end=end,
                    token_count=len(tokens),
                    idn_count=len(idn),
                    con_count=len(con),
                ))

        def fail(message: str, start: int, end: int, from_state: str, symbol: str) -> None:
            record(from_state, "SE", message, symbol, start, end)
            raise LexicalError(
                line=text.count("\n", 0, max(0, min(start, len(text)))) + 1,
                column=column_at(start),
                message=message,
                start=start,
                end=max(start + 1, end),
                partial_result=LexerResult(tokens, idn, con, steps),
            )

        while True:
            char = text[i] if i < len(text) else None
            symbol = repr(char) if char is not None else "EOF"

            if state == "S0":
                if char is None:
                    record("S0", "FIN", "Кінець вхідного тексту", "EOF", i, i)
                    break
                if char in " \t":
                    record("S0", "SKIP", "Пробільний символ", symbol, i, i + 1)
                    record("SKIP", "S0", "Пропущено", symbol, i, i + 1)
                    i += 1
                elif char == "\n":
                    token_start = i
                    lexeme, code, index = "¶", NEWLINE, None
                    i += 1
                    record("S0", "NL", "Роздільник нового рядка", "\\n", token_start, i)
                    record("NL", "S10", "Підготовлено ¶ (код 36)", "\\n", token_start, i)
                    state = "S10"
                elif "a" <= char <= "z":
                    token_start = i
                    lexeme, index = char, None
                    i += 1
                    record("S0", "S1", "Початок слова", symbol, token_start, i)
                    state = "S1"
                elif "0" <= char <= "9":
                    token_start = i
                    lexeme, index = char, None
                    i += 1
                    record("S0", "S2", "Початок числа", symbol, token_start, i)
                    state = "S2"
                elif char in ":<>=!":
                    token_start = i
                    lexeme, index = char, None
                    i += 1
                    state = {":": "S3", "<": "S4", ">": "S5", "=": "S6", "!": "S7"}[char]
                    record("S0", state, "Початок оператора", symbol, token_start, i)
                elif char in SINGLE_CHAR_TOKENS:
                    token_start = i
                    lexeme, code, index = char, SINGLE_CHAR_TOKENS[char], None
                    i += 1
                    record("S0", "OP", "Односимвольна лексема", symbol, token_start, i)
                    record("OP", "S10", f"Присвоєно код {code}", symbol, token_start, i)
                    state = "S10"
                else:
                    fail(f"недопустимий символ {char!r}", i, i + 1, "S0", symbol)

            elif state == "S1":
                if char is not None and ("a" <= char <= "z" or "0" <= char <= "9"):
                    lexeme += char
                    record("S1", "S1", "Продовжуємо слово", symbol, i, i + 1)
                    i += 1
                else:
                    record("S1", "S8", "Кінець слова; символ не поглинається", symbol, token_start, i)
                    state = "S8"

            elif state == "S8":
                record("S8", "D", "Перевірити end.", symbol, token_start, i)
                if lexeme == "end" and char == ".":
                    i += 1
                    lexeme, code = "end.", END_PROGRAM
                    record("D", "END", "Поглинули крапку, код 5", "'.'", token_start, i)
                    record("END", "S10", "Спеціальна лексема end.", "'.'", token_start, i)
                else:
                    record("D", "K", "Звичайне слово або ключове", symbol, token_start, i)
                    if lexeme in KEYWORDS:
                        code = KEYWORDS[lexeme]
                        record("K", "KW", f"Ключове слово, код {code}", symbol, token_start, i)
                        record("KW", "S10", "Готова лексема", symbol, token_start, i)
                    else:
                        code = IDENTIFIER
                        if lexeme not in idn_indices:
                            idn.append(lexeme)
                            idn_indices[lexeme] = len(idn)
                        index = idn_indices[lexeme]
                        record("K", "ID", f"Ідентифікатор, індекс IDN {index}", symbol, token_start, i)
                        record("ID", "S10", "Готова лексема", symbol, token_start, i)
                state = "S10"

            elif state == "S2":
                if char is not None and "0" <= char <= "9":
                    lexeme += char
                    record("S2", "S2", "Продовжуємо число", symbol, i, i + 1)
                    i += 1
                elif char is not None and (("a" <= char <= "z") or char.isalpha() or char == "."):
                    fail(f"некоректна ціла константа біля {lexeme + char!r}",
                         token_start, i + 1, "S2", symbol)
                else:
                    record("S2", "S9", "Кінець числа; символ не поглинається", symbol, token_start, i)
                    state = "S9"

            elif state == "S9":
                code = CONSTANT
                if lexeme not in con_indices:
                    con.append(lexeme)
                    con_indices[lexeme] = len(con)
                index = con_indices[lexeme]
                record("S9", "S10", f"Константа, індекс CON {index}", symbol, token_start, i)
                state = "S10"

            elif state in ("S3", "S4", "S5", "S6", "S7"):
                node_if_equals = {"S3": "ASSIGN", "S4": "LE", "S5": "GE", "S6": "EQ", "S7": "NE"}
                node_other = {"S3": "COLON", "S4": "LT", "S5": "GT", "S6": "SET"}
                previous = state
                if char == "=":
                    lexeme += "="
                    i += 1
                    code = DOUBLE_CHAR_TOKENS[lexeme]
                    node = node_if_equals[previous]
                    record(previous, node, f"Двосимвольний оператор {lexeme}, код {code}", "'='", token_start, i)
                elif previous == "S7":
                    fail("символ '!' допускається тільки в операторі '!='",
                         token_start, token_start + 1, "S7", symbol)
                else:
                    code = SINGLE_CHAR_TOKENS[lexeme]
                    node = node_other[previous]
                    record(previous, node, f"Односимвольний оператор {lexeme}, код {code}; наступний символ не поглинається",
                           symbol, token_start, i)
                record(node, "S10", "Оператор розпізнано", symbol, token_start, i)
                state = "S10"

            elif state == "S10":
                token = Token(lexeme=lexeme, code=code, line=line, index=index)
                tokens.append(token)
                record("S10", "S0", f"Записано {lexeme!r} (код {code})", lexeme, token_start, i)
                if lexeme == "¶":
                    line += 1
                    line_start = i
                state = "S0"
            else:
                raise RuntimeError(f"Невідомий стан: {state}")

        return LexerResult(tokens, idn, con, steps)
