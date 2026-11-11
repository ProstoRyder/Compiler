"""ЛР №3. Синтаксичний аналізатор методом рекурсивного спуску.

Працює з Token, сформованими лексером лабораторної №2. Не виконує код.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager

from lexer import Lexer, Token
from tokens import CONSTANT, IDENTIFIER, NEWLINE


class SyntaxAnalysisError(Exception):
    def __init__(self, line: int, message: str, token_index: int = 0):
        self.line = line
        self.message = message
        self.token_index = token_index
        super().__init__(f"Рядок {line}: {message}")


@dataclass(frozen=True)
class ParseStep:
    number: int
    line: int
    token: str
    rule: str
    action: str
    stack: str


class Parser:
    RELATIONS = {29, 30, 31, 32, 33, 34}

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.position = 0
        self.steps: list[ParseStep] = []
        self._stack: list[str] = []

    @property
    def current(self) -> Token | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _line(self) -> int:
        if self.current:
            return self.current.line
        if not self.tokens:
            return 1
        last = self.tokens[-1]
        return last.line + (1 if last.code == NEWLINE else 0)

    def _record(self, action: str) -> None:
        token = self.current
        self.steps.append(ParseStep(
            len(self.steps) + 1, self._line(), token.lexeme if token else 'EOF',
            self._stack[-1] if self._stack else 'програма', action,
            ' → '.join(self._stack) or '—',
        ))

    @contextmanager
    def _rule(self, name: str):
        self._stack.append(name)
        self._record('Вхід у правило')
        try:
            yield
            self._record('Успішне завершення правила')
        finally:
            self._stack.pop()

    def error(self, message: str) -> None:
        self._record('ПОМИЛКА: ' + message)
        raise SyntaxAnalysisError(self._line(), message, self.position)

    def match(self, code: int) -> bool:
        return self.current is not None and self.current.code == code

    def accept(self, code: int) -> bool:
        if self.match(code):
            self.expect(code, repr(self.current.lexeme))
            return True
        return False

    def expect(self, code: int, description: str) -> Token:
        if not self.match(code):
            actual = repr(self.current.lexeme) if self.current else 'кінець файлу'
            self.error(f'очікується {description}, отримано {actual}')
        token = self.current
        self._record(f'Прочитано {token.lexeme!r} (код {token.code})')
        self.position += 1
        return token

    def parse(self) -> None:
        with self._rule('програма'):
            self.expect(1, "'program'")
            self.expect(IDENTIFIER, 'назва програми')
            self.expect(NEWLINE, 'новий рядок після назви програми')
            self.expect(2, "'var'")
            self.parse_id_list()
            self.expect(19, "':'")
            self.expect(3, "'integer'")
            self.expect(NEWLINE, 'новий рядок після оголошення змінних')
            self.expect(4, "'begin'")
            self.expect(NEWLINE, "новий рядок після 'begin'")
            self.parse_statement_list(5)
            self.expect(5, "'end.' для завершення програми")
            # Допускається один завершальний перенос рядка файла.
            self.accept(NEWLINE)
            if self.current:
                self.error('зайві лексеми після завершення програми')
            self._record('Синтаксис програми правильний')

    def parse_id_list(self) -> None:
        with self._rule('список ідентифікаторів'):
            self.expect(IDENTIFIER, 'ідентифікатор')
            while self.accept(18):
                self.expect(IDENTIFIER, "ідентифікатор після ','")

    def parse_statement_list(self, terminator: int) -> None:
        with self._rule('список операторів'):
            if self.match(terminator):
                self.error('очікується хоча б один оператор')
            self.parse_statement()
            while self.accept(NEWLINE):
                if self.match(terminator):
                    return
                self.parse_statement()
            self.error('очікується перехід на новий рядок перед завершенням блоку')

    def parse_statement(self) -> None:
        with self._rule('оператор'):
            if self.match(IDENTIFIER):
                self.expect(IDENTIFIER, 'ідентифікатор')
                self.expect(20, "':=' для присвоєння")
                self.parse_expression()
            elif self.match(6) or self.match(7):
                keyword = self.current.code
                self.expect(keyword, "'read' або 'write'")
                self.expect(27, "'('")
                self.parse_id_list()
                self.expect(28, "')'")
            elif self.match(8):
                self.parse_for()
            elif self.match(12):
                self.parse_if()
            elif self.match(27):
                self.parse_ternary()
            else:
                self.error('очікується оператор присвоєння, read, write, for, if або тернарний оператор')

    def parse_for(self) -> None:
        with self._rule('цикл for'):
            self.expect(8, "'for'")
            self.expect(IDENTIFIER, 'ідентифікатор лічильника циклу')
            self.expect(21, "'=' у заголовку циклу")
            self.parse_expression()
            self.expect(9, "'to'")
            self.parse_expression()
            self.expect(10, "'do'")
            self.expect(NEWLINE, "новий рядок після 'do'")
            self.parse_statement_list(11)
            self.expect(11, "'end' для завершення циклу")

    def parse_if(self) -> None:
        with self._rule('умовний оператор if'):
            self.expect(12, "'if'")
            self.parse_relation()
            self.expect(13, "'then'")
            self.parse_statement()
            self.expect(14, "'else'")
            self.parse_statement()

    def parse_ternary(self) -> None:
        with self._rule('тернарний оператор'):
            self.expect(27, "'('")
            self.expect(IDENTIFIER, 'ідентифікатор результату тернарного оператора')
            self.expect(21, "'=' після ідентифікатора")
            self.parse_logical_expression()
            self.expect(35, "'?'")
            self.parse_expression()
            self.expect(19, "':'")
            self.parse_expression()
            self.expect(28, "')' у кінці тернарного оператора")

    def parse_relation(self) -> None:
        with self._rule('відношення'):
            self.parse_expression()
            if self.current is None or self.current.code not in self.RELATIONS:
                self.error('очікується знак відношення (<, >, <=, >=, ==, !=)')
            code = self.current.code
            self.expect(code, 'знак відношення')
            self.parse_expression()

    def parse_logical_expression(self) -> None:
        with self._rule('логічний вираз'):
            self.parse_logical_term()
            while self.accept(17):
                self.parse_logical_term()

    def parse_logical_term(self) -> None:
        with self._rule('логічний доданок'):
            self.parse_logical_factor()
            while self.accept(16):
                self.parse_logical_factor()

    def parse_logical_factor(self) -> None:
        with self._rule('логічний множник'):
            if self.accept(15):
                self.parse_logical_factor()
                return
            # Спробувати (логічний вираз), але (a + b) > c є відношенням.
            # Контрольна точка дає змогу розрізнити їх без зміни лексера.
            if self.match(27):
                checkpoint = self.position
                steps_checkpoint = len(self.steps)
                try:
                    self.expect(27, "'('")
                    self.parse_logical_expression()
                    self.expect(28, "')' у логічному виразі")
                    return
                except SyntaxAnalysisError:
                    self.position = checkpoint
                    del self.steps[steps_checkpoint:]
            self.parse_relation()

    def parse_expression(self) -> None:
        with self._rule('арифметичний вираз'):
            self.parse_term()
            while self.current is not None and self.current.code in (22, 23):
                self.expect(self.current.code, "'+' або '-'")
                self.parse_term()

    def parse_term(self) -> None:
        with self._rule('доданок'):
            self.parse_power()
            while self.current is not None and self.current.code in (24, 25):
                self.expect(self.current.code, "'*' або '/'")
                self.parse_power()

    def parse_power(self) -> None:
        with self._rule('степінь'):
            self.parse_factor()
            if self.accept(26):
                self.parse_power()  # права асоціативність

    def parse_factor(self) -> None:
        with self._rule('множник'):
            if self.current and self.current.code in (IDENTIFIER, CONSTANT):
                self.expect(self.current.code, 'ідентифікатор або константа')
            elif self.accept(27):
                self.parse_expression()
                self.expect(28, "')' після арифметичного виразу")
            else:
                self.error('очікується число, ідентифікатор або вираз у дужках')


def analyze(source: str) -> Parser:
    """Виконати лексичний і синтаксичний аналіз, повернути парсер із трасою."""
    result = Lexer().scan(source)
    parser = Parser(result.tokens)
    parser.parse()
    return parser
