import unittest
from lexer import Lexer
from parser import Parser, SyntaxAnalysisError, analyze
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def program(*statements):
    return 'program demo\nvar a, b, i, n, result: integer\nbegin\n' + '\n'.join(statements) + '\nend.\n'


class ParserFullTests(unittest.TestCase):
    def test_original_complete_example(self):
        source = (ROOT / 'examples' / 'valid.txt').read_text(encoding='utf-8')
        self.assertGreater(len(analyze(source).steps), 100)

    def test_read_write(self):
        analyze(program('read(a, b, n)', 'write(a, b)'))

    def test_empty_read_is_error(self):
        with self.assertRaisesRegex(SyntaxAnalysisError, 'ідентифікатор'):
            analyze(program('read()'))

    def test_numbers_cannot_be_written(self):
        with self.assertRaises(SyntaxAnalysisError):
            analyze(program('write(12)'))

    def test_if_nested(self):
        analyze(program('if a > b then if a == n then result := 1 else result := 2 else result := 3'))

    def test_missing_then_line(self):
        with self.assertRaises(SyntaxAnalysisError) as context:
            analyze(program('if a > b result := a else result := b'))
        self.assertEqual(context.exception.line, 4)
        self.assertIn('then', str(context.exception))

    def test_missing_else(self):
        with self.assertRaisesRegex(SyntaxAnalysisError, 'else'):
            analyze(program('if a > b then result := a'))

    def test_for_nested(self):
        analyze(program('for i = 1 to n do', 'for a = 0 to b do', 'result := result + a', 'end', 'end', 'write(result)'))

    def test_missing_for_end(self):
        with self.assertRaises(SyntaxAnalysisError):
            analyze(program('for i = 1 to 3 do', 'a := 1'))

    def test_ternary_logic_and_parentheses(self):
        analyze(program('(result = not (a > b or (a + 2) <= n) and i != 0 ? a ↑ 2 : b + 3)'))

    def test_ternary_missing_question(self):
        with self.assertRaisesRegex(SyntaxAnalysisError, '\\?'):
            analyze(program('(result = a > b a : b)'))

    def test_no_unary_minus(self):
        with self.assertRaises(SyntaxAnalysisError):
            analyze(program('result := -5'))

    def test_no_same_line_separation(self):
        with self.assertRaises(SyntaxAnalysisError):
            analyze(program('a := 1 b := 2'))

    def test_empty_block_is_error(self):
        with self.assertRaises(SyntaxAnalysisError):
            analyze('program demo\nvar a: integer\nbegin\nend.\n')

    def test_extra_tokens(self):
        with self.assertRaises(SyntaxAnalysisError):
            analyze(program('a := 1') + 'write(a)')

    def test_source_line_for_error(self):
        with self.assertRaises(SyntaxAnalysisError) as context:
            analyze(program('a := 1', 'b := 2 +'))
        self.assertEqual(context.exception.line, 5)

    def test_parse_step_has_stack(self):
        p = analyze(program('a := 1'))
        self.assertTrue(any('арифметичний вираз' in s.stack for s in p.steps))
        self.assertTrue(any('Синтаксис програми правильний' in s.action for s in p.steps))


if __name__ == '__main__':
    unittest.main()
