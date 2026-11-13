import unittest
from dataclasses import dataclass
from poliz_expressions import PolizExpressionError, convert_expression


@dataclass
class Token:
    lexeme: str
    code: int
    line: int = 1
    index: int | None = None


class TestShuntingYard(unittest.TestCase):
    def check(self, source, expected):
        result = convert_expression(source.split())
        self.assertEqual(result.poliz, tuple(expected.split()))
        self.assertEqual(len(result.steps), len(source.split()) + 1)

    def test_multiplication_before_addition(self):
        self.check("5 + 2 * 3", "5 2 3 * +")

    def test_parentheses(self):
        self.check("( 5 + 2 ) * 3", "5 2 + 3 *")

    def test_right_associative_power(self):
        self.check("2 ↑ 3 ↑ 2", "2 3 2 ↑ ↑")

    def test_left_associative_subtract(self):
        self.check("8 - 3 - 1", "8 3 - 1 -")

    def test_source_from_previous_lab(self):
        self.check(
            "( sum + 2 ) * 3 - 8 / 2 + 2 ↑ 3",
            "sum 2 + 3 * 8 2 / - 2 3 ↑ +",
        )

    def test_accepts_existing_token_objects(self):
        ts = [Token("a", 37), Token("+", 22), Token("2", 38)]
        result = convert_expression(ts)
        self.assertEqual(result.poliz, ("a", "2", "+"))

    def test_unary_minus_rejected_by_default(self):
        with self.assertRaises(PolizExpressionError):
            convert_expression("- 2 + 3".split())

    def test_optional_unary_minus(self):
        result = convert_expression(
            "- 2 ↑ 2".split(), enable_unary_minus=True
        )
        self.assertEqual(result.poliz, ("2", "2", "↑", "NEG"))

    def test_unary_minus_as_power_operand(self):
        result = convert_expression("2 ↑ - 3".split(), enable_unary_minus=True)
        self.assertEqual(result.poliz, ("2", "3", "NEG", "↑"))

    def test_incomplete_expression(self):
        with self.assertRaises(PolizExpressionError):
            convert_expression("a +".split())

    def test_unbalanced_parentheses(self):
        with self.assertRaises(PolizExpressionError):
            convert_expression("( a + 2".split())


if __name__ == "__main__":
    unittest.main(verbosity=2)
