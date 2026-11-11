import unittest
from parser import Parser, SyntaxAnalysisError, analyze
from lexer import Lexer


class ParserFirstStepTests(unittest.TestCase):
    def test_valid_assignments(self):
        source = 'program test\nvar a, b: integer\nbegin\na := 5 + 2 * 3\nb := (a + 1) ↑ 2\nend.\n'
        analyze(source)

    def test_missing_operand_reports_line(self):
        source = 'program test\nvar a: integer\nbegin\na := 5 +\nend.'
        with self.assertRaises(SyntaxAnalysisError) as caught:
            analyze(source)
        self.assertEqual(caught.exception.line, 4)
        self.assertIn('очікується число', str(caught.exception))

    def test_missing_type_reports_line(self):
        source = 'program test\nvar a:\nbegin\na := 1\nend.'
        with self.assertRaises(SyntaxAnalysisError) as caught:
            analyze(source)
        self.assertEqual(caught.exception.line, 2)
        self.assertIn("'integer'", str(caught.exception))

    def test_trailing_tokens_rejected(self):
        source = 'program test\nvar a: integer\nbegin\na := 1\nend.\na := 2'
        with self.assertRaises(SyntaxAnalysisError):
            analyze(source)


if __name__ == '__main__':
    unittest.main()
