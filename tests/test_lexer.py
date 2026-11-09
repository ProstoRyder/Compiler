import unittest
from pathlib import Path
from lexer import Lexer, LexicalError


class LexerTests(unittest.TestCase):
    def setUp(self):
        self.lexer = Lexer()

    def test_full_example(self):
        source = (Path(__file__).parent.parent / "examples" / "valid.txt").read_text(encoding="utf-8").rstrip("\n")
        res = self.lexer.scan(source)
        self.assertEqual(res.idn, ["example", "a", "b", "i", "n", "sum", "result"])
        self.assertEqual(res.con, ["0", "1", "2", "3", "8"])
        self.assertEqual((res.tokens[-1].lexeme, res.tokens[-1].code), ("end.", 5))
        self.assertEqual(sum(tok.code == 36 for tok in res.tokens), 14)
        self.assertEqual([tok.code for tok in res.tokens[:3]], [1, 37, 36])

    def test_operators(self):
        result = self.lexer.scan("a<=b>=c==d!=e:=f")
        self.assertEqual([(x.lexeme, x.code) for x in result.tokens if x.code != 37],
                         [("<=", 31), (">=", 32), ("==", 33), ("!=", 34), (":=", 20)])

    def test_no_spaces(self):
        result = self.lexer.scan("sum:=sum+i")
        self.assertEqual([t.lexeme for t in result.tokens], ["sum", ":=", "sum", "+", "i"])
        self.assertEqual(result.idn, ["sum", "i"])

    def test_errors(self):
        for text in ("a ! b", "a := 12.5", "a := 123abc", "a := @"):
            with self.subTest(text=text), self.assertRaises(LexicalError):
                self.lexer.scan(text)

    def test_minus_is_token(self):
        result = self.lexer.scan("a := -5")
        self.assertEqual([t.code for t in result.tokens], [37, 20, 23, 38])


if __name__ == "__main__":
    unittest.main()
