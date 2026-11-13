from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from lexer import Token
from parser import Parser, SyntaxAnalysisError
from tokens import IDENTIFIER, NEWLINE
from poliz_expressions import convert_expression


@dataclass(frozen=True)
class PolizStep:
    number: int
    line: int
    lexeme: str
    operator_stack: tuple[str, ...]
    output: tuple[str, ...]
    action: str
    token_index: int | None = None


@dataclass(frozen=True)
class PolizResult:
    code: tuple[str, ...]
    steps: tuple[PolizStep, ...]

    @property
    def text(self) -> str:
        return ' '.join(self.code)


class PolizGenerationError(ValueError):
    pass


class PolizGenerator:

    RELATIONS = {29, 30, 31, 32, 33, 34}

    def __init__(self, tokens: Sequence[Token]):
        self.tokens = list(tokens)
        self.position = 0
        self.code: list[str] = []
        self.steps: list[PolizStep] = []
        self.control_stack: list[str] = []
        self.label_index = 0
        self.temp_index = 0

    def _current(self) -> Token | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _at(self, code: int) -> bool:
        return self._current() is not None and self._current().code == code

    def _trace(self, lexeme: str, action: str, *, line: int | None = None,
               ops: tuple[str, ...] = (), token_index: int | None = None) -> None:
        if line is None:
            near = self.tokens[min(self.position, len(self.tokens)-1)] if self.tokens else None
            line = near.line if near else 1
        self.steps.append(PolizStep(
            number=len(self.steps) + 1,
            line=line,
            lexeme=lexeme,
            operator_stack=tuple(self.control_stack) + ops,
            output=tuple(self.code),
            action=action,
            token_index=token_index,
        ))

    def _take(self, code: int, *, action: str = 'Прочитано лексему',
              emit_value: bool = False) -> Token:
        token = self._current()
        if token is None or token.code != code:
            actual = token.lexeme if token else 'EOF'
            raise PolizGenerationError(f'Очікується код {code}, отримано {actual!r}')
        index = self.position
        self.position += 1
        if emit_value:
            self.code.append(token.lexeme)
            action = 'Операнд додано до ПОЛІЗ'
        self._trace(token.lexeme, action, line=token.line, token_index=index)
        return token

    def _emit(self, *items: str, action: str) -> None:
        self.code.extend(items)
        self._trace('—', action)

    def _label(self) -> str:
        self.label_index += 1
        return f'L{self.label_index}'

    def _temp(self) -> str:
        self.temp_index += 1
        return f'$T{self.temp_index}'

    def generate(self, *, validate: bool = True) -> PolizResult:
        if validate:
            Parser(self.tokens).parse()
        self._take(1)
        self._take(IDENTIFIER)
        self._take(NEWLINE)
        self._take(2)
        self._parse_identifier_list(output_action=None)  # оголошення
        self._take(19)
        self._take(3)
        self._take(NEWLINE)
        self._take(4)
        self._take(NEWLINE)
        self._parse_statement_list(5)
        self._take(5)
        if self._at(NEWLINE):
            self._take(NEWLINE)
        if self.position != len(self.tokens):
            raise PolizGenerationError('Зайві лексеми після end.')
        self._trace('EOF', 'Побудову ПОЛІЗ завершено')
        return PolizResult(tuple(self.code), tuple(self.steps))

    def _parse_identifier_list(self, *, output_action: str | None) -> None:
        while True:
            self._take(IDENTIFIER, emit_value=output_action is not None)
            if output_action is not None:
                self._emit(output_action, action=f'Оператор {output_action}')
            if not self._at(18):
                break
            self._take(18)

    def _parse_statement_list(self, terminator: int) -> None:
        self._parse_statement()
        while self._at(NEWLINE):
            self._take(NEWLINE)
            if self._at(terminator):
                return
            self._parse_statement()
        raise PolizGenerationError('Очікується новий рядок наприкінці блоку')

    def _parse_statement(self) -> None:
        if self._at(IDENTIFIER):
            self._take(IDENTIFIER, emit_value=True)
            self._take(20)  # :=
            self._parse_expression()
            self._emit(':=', action='Завершено присвоєння')
        elif self._at(6):
            self._take(6)
            self._take(27)
            self._parse_identifier_list(output_action='READ')
            self._take(28)
        elif self._at(7):
            self._take(7)
            self._take(27)
            self._parse_identifier_list(output_action='WRITE')
            self._take(28)
        elif self._at(8):
            self._parse_for()
        elif self._at(12):
            self._parse_if()
        elif self._at(27):
            self._parse_ternary()
        else:
            token = self._current()
            raise PolizGenerationError(f'Неочікуваний оператор: {token.lexeme if token else "EOF"}')

    def _parse_expression(self) -> None:
        probe = Parser(self.tokens)
        probe.position = self.position
        probe.parse_expression()
        last = probe.position
        subset = self.tokens[self.position:last]
        postfix = convert_expression(subset)
        old_size = 0
        for i, step in enumerate(postfix.steps):
            additions = step.output[old_size:]
            self.code.extend(additions)
            old_size = len(step.output)
            if i < len(subset):
                source = subset[i]
                self._trace(source.lexeme, step.action, ops=step.operator_stack,
                            line=source.line, token_index=self.position + i)
            else:
                self._trace('кінець виразу', step.action, ops=step.operator_stack,
                            line=subset[-1].line)
        self.position = last

    def _parse_relation(self) -> None:
        self._parse_expression()
        token = self._current()
        if token is None or token.code not in self.RELATIONS:
            raise PolizGenerationError('Очікується оператор відношення')
        relation = self._take(token.code).lexeme
        self._parse_expression()
        self._emit(relation, action=f'Виконати порівняння {relation}')

    def _parse_logical_expression(self) -> None:
        self._parse_logical_term()
        while self._at(17):
            self._take(17)
            self._parse_logical_term()
            self._emit('or', action='Об’єднання логічних значень (or)')

    def _parse_logical_term(self) -> None:
        self._parse_logical_factor()
        while self._at(16):
            self._take(16)
            self._parse_logical_factor()
            self._emit('and', action='Об’єднання логічних значень (and)')

    def _parse_logical_factor(self) -> None:
        if self._at(15):
            self._take(15)
            self._parse_logical_factor()
            self._emit('not', action='Логічне заперечення')
            return
        if self._at(27):
            checkpoint = (self.position, len(self.code), len(self.steps),
                          self.label_index, self.temp_index)
            try:
                self._take(27)
                self._parse_logical_expression()
                self._take(28)
                return
            except (SyntaxAnalysisError, PolizGenerationError, ValueError):
                self.position, code_size, steps_size, self.label_index, self.temp_index = checkpoint
                del self.code[code_size:]
                del self.steps[steps_size:]
        self._parse_relation()

    def _parse_if(self) -> None:
        self._take(12)
        false_label = self._label()
        end_label = self._label()
        self.control_stack.append(f'if → {false_label}')
        self._parse_relation()
        self._take(13)  # then
        self._emit(false_label, 'УПХ', action=f'Хибна умова → {false_label}')
        self._parse_statement()
        self._take(14)  # else
        self._emit(end_label, 'БП', action=f'Пропустити else → {end_label}')
        self._emit(f'{false_label}:', action='Мітка гілки else')
        self._parse_statement()
        self._emit(f'{end_label}:', action='Мітка завершення if')
        self.control_stack.pop()

    def _parse_for(self) -> None:
        self._take(8)
        index = self._take(IDENTIFIER, emit_value=True).lexeme
        self._take(21)  # =
        self._parse_expression()
        self._emit(':=', action='Ініціалізація лічильника циклу')
        self._take(9)  # to
        bound = self._temp()
        self._emit(bound, action='Тимчасова змінна для верхньої межі')
        self._parse_expression()
        self._emit(':=', action='Обчислення верхньої межі циклу один раз')
        self._take(10)  # do
        self._take(NEWLINE)
        start_label, end_label = self._label(), self._label()
        self.control_stack.append(f'for → {start_label}')
        self._emit(f'{start_label}:', action='Початок перевірки умови циклу')
        self._emit(index, bound, '<=', end_label, 'УПХ', action='Вихід із циклу, якщо i > межі')
        self._parse_statement_list(11)
        self._take(11)  # end
        self._emit(index, index, '1', '+', ':=', action='Збільшення лічильника на 1')
        self._emit(start_label, 'БП', action='Повернення до перевірки циклу')
        self._emit(f'{end_label}:', action='Мітка виходу з циклу')
        self.control_stack.pop()

    def _parse_ternary(self) -> None:
        self._take(27)
        variable = self._take(IDENTIFIER).lexeme
        self._take(21)  # =
        false_label, end_label = self._label(), self._label()
        self.control_stack.append(f'?: → {false_label}')
        self._parse_logical_expression()
        self._take(35)  # ?
        self._emit(false_label, 'УПХ', action='Тернарний: хибна гілка')
        self._emit(variable, action='Адреса результату істинної гілки')
        self._parse_expression()
        self._emit(':=', end_label, 'БП', action='Присвоїти істинний вираз і пропустити хибний')
        self._take(19)  # :
        self._emit(f'{false_label}:', variable, action='Мітка та адреса хибної гілки')
        self._parse_expression()
        self._emit(':=', action='Присвоїти результат хибного виразу')
        self._take(28)  # )
        self._emit(f'{end_label}:', action='Завершення тернарного оператора')
        self.control_stack.pop()


def generate_poliz(tokens: Sequence[Token], *, validate: bool = True) -> PolizResult:
    return PolizGenerator(tokens).generate(validate=validate)
