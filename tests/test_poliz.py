from __future__ import annotations

from pathlib import Path
import unittest

from lexer import Lexer
from parser import SyntaxAnalysisError
from poliz import generate_poliz

ROOT = Path(__file__).resolve().parents[1]


def program(*statements):
    return ('program test\nvar a, b, i, n, result: integer\nbegin\n'
            + '\n'.join(statements) + '\nend.\n')


def compile_source(source):
    return generate_poliz(Lexer().scan(source).tokens)


def execute_for_test(code, inputs=()):
    """Контрольна тестова стек-машина — перевірка логіки отриманих переходів."""
    code = list(code)
    marks = {w[:-1]: index for index, w in enumerate(code) if w.endswith(':')}
    stack, variables, printed = [], {}, []
    inputs = iter(inputs)
    pc = 0
    steps = 0

    def val(raw):
        if isinstance(raw, bool) or isinstance(raw, int):
            return raw
        if raw.isdecimal():
            return int(raw)
        return variables.get(raw, 0)

    binary = {
        '+': lambda a,b: a+b, '-': lambda a,b: a-b,
        '*': lambda a,b: a*b, '/': lambda a,b: a//b,
        '↑': lambda a,b: a**b,
        '<': lambda a,b: a<b, '>': lambda a,b: a>b,
        '<=': lambda a,b: a<=b, '>=': lambda a,b: a>=b,
        '==': lambda a,b: a==b, '!=': lambda a,b: a!=b,
        'and': lambda a,b: bool(a) and bool(b),
        'or': lambda a,b: bool(a) or bool(b),
    }
    while pc < len(code):
        steps += 1
        if steps > 10000:
            raise AssertionError('Цикл не завершується')
        op = code[pc]
        pc += 1
        if op.endswith(':'):
            continue
        if op in binary:
            b = val(stack.pop())
            a = val(stack.pop())
            stack.append(binary[op](a,b))
        elif op == 'not':
            stack.append(not val(stack.pop()))
        elif op == ':=':
            rhs = val(stack.pop())
            lhs = stack.pop()
            variables[lhs] = rhs
        elif op == 'READ':
            variables[stack.pop()] = next(inputs)
        elif op == 'WRITE':
            printed.append(val(stack.pop()))
        elif op in ('УПХ', 'БП'):
            target = stack.pop()
            if op == 'БП' or not val(stack.pop()):
                pc = marks[target] + 1
        else:
            stack.append(op)
    if stack:
        raise AssertionError(f'У стеку залишилися дані: {stack!r}')
    return variables, printed


class PolizTests(unittest.TestCase):
    def test_previous_full_example(self):
        src = (ROOT / 'examples' / 'valid.txt').read_text(encoding='utf-8')
        result = compile_source(src)
        self.assertEqual(result.code[:6], ('a','READ','b','READ','n','READ'))
        self.assertIn('УПХ', result.code)
        self.assertIn('БП', result.code)
        self.assertIn('↑', result.code)
        vars, printed = execute_for_test(result.code, inputs=(4, 2, 3))
        self.assertEqual(vars['sum'], 6)
        self.assertEqual(vars['result'], 28)  # (6 + 2) * 3 - 8 / 2 + 2 ↑ 3
        self.assertEqual(printed[-1], vars['result'])

    def test_arithmetic_precedence_and_power(self):
        res = compile_source(program('a := 2 ↑ 3 ↑ 2 + (5 - 1) * 2', 'write(a)'))
        self.assertEqual(res.code, ('a','2','3','2','↑','↑','5','1','-','2','*','+',' := '.strip(),'a','WRITE'))
        variables, printed = execute_for_test(res.code)
        self.assertEqual(printed, [520])
        self.assertEqual(variables['a'], 520)

    def test_if_branches(self):
        for inp, expected in ((1,10), (9,20)):
            with self.subTest(inp=inp):
                res = compile_source(program('read(a)', 'if a < 5 then b := 10 else b := 20', 'write(b)'))
                variables, printed = execute_for_test(res.code, inputs=(inp,))
                self.assertEqual(printed, [expected])
                self.assertEqual(variables['b'], expected)

    def test_for_with_bound_evaluated_once(self):
        src = program('n := 3','a := 0','for i = 1 to n do',
                      'a := a + i','n := 10','end','write(a)')
        res = compile_source(src)
        vars, printed = execute_for_test(res.code)
        self.assertEqual(printed, [6])
        self.assertEqual(vars['$T1'], 3)

    def test_nested_loop_and_if(self):
        src = program('a := 0', 'for i = 1 to 3 do',
                      'if i == 2 then a := a + 100 else a := a + i',
                      'end', 'write(a)')
        result = compile_source(src)
        self.assertEqual(execute_for_test(result.code)[1], [104])
        self.assertEqual(len(set(tok[:-1] for tok in result.code if tok.endswith(':'))), 4)

    def test_ternary_complex_condition(self):
        src = program('a := 1', 'b := 2', 'n := 3',
            '(result = not (a > b or (a + 2) <= n) and b != 0 ? a ↑ 2 : b + 3)',
            'write(result)')
        result = compile_source(src)
        self.assertEqual(execute_for_test(result.code)[1], [5])

    def test_ternary_true_branch(self):
        src = program('a := 4', 'b := 2', '(result = a > b ? a * 2 : b)', 'write(result)')
        self.assertEqual(execute_for_test(compile_source(src).code)[1], [8])

    def test_all_input_tokens_traced_once(self):
        src = (ROOT / 'examples' / 'valid.txt').read_text(encoding='utf-8')
        toks = Lexer().scan(src).tokens
        result = generate_poliz(toks)
        indices = [s.token_index for s in result.steps if s.token_index is not None]
        self.assertEqual(indices, list(range(len(toks))))
        self.assertTrue(any(step.operator_stack and '*' in step.operator_stack for step in result.steps))
        self.assertEqual(result.steps[-1].output, result.code)

    def test_bad_syntax_does_not_generate(self):
        src = program('a := -3')
        with self.assertRaises(SyntaxAnalysisError):
            compile_source(src)


if __name__ == '__main__':
    unittest.main()
