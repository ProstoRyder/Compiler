import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from exporter import export_csv
from lexer import Lexer, LexicalError


class BonusFeatureTests(unittest.TestCase):
    def setUp(self):
        self.lexer = Lexer()

    def test_trace_states_and_counts(self):
        result = self.lexer.scan("sum:=sum+i", trace=True)
        states = [(step.state, step.next_state) for step in result.steps]
        self.assertIn(("S0", "S1"), states)
        self.assertIn(("S1", "S8"), states)
        self.assertIn(("D", "K"), states)
        self.assertIn(("K", "ID"), states)
        self.assertIn(("S3", "ASSIGN"), states)
        self.assertIn(("S10", "S0"), states)
        self.assertEqual(result.steps[-1].next_state, "FIN")
        self.assertEqual(result.steps[-1].token_count, 5)
        self.assertEqual(result.steps[-1].idn_count, 2)

    def test_trace_integrates_end_and_newline(self):
        result = self.lexer.scan("end\nend.", trace=True)
        self.assertEqual([(t.lexeme, t.code, t.line) for t in result.tokens],
                         [("end", 11, 1), ("¶", 36, 1), ("end.", 5, 2)])
        states = [(step.state, step.next_state) for step in result.steps]
        self.assertIn(("D", "END"), states)
        self.assertIn(("S0", "NL"), states)
        self.assertEqual(result.steps[-1].next_state, "FIN")

    def test_error_marks_invalid_character(self):
        source = "a:=1\nresult:=@"
        with self.assertRaises(LexicalError) as err:
            self.lexer.scan(source, trace=True)
        exc = err.exception
        self.assertEqual((exc.line, exc.column), (2, 9))
        self.assertEqual(source[exc.start:exc.end], "@")
        self.assertEqual(exc.partial_result.steps[-1].next_state, "SE")
        self.assertEqual([t.lexeme for t in exc.partial_result.tokens],
                         ["a", ":=", "1", "¶", "result", ":="])

    def test_error_marks_invalid_number(self):
        source = "a:=12.5"
        with self.assertRaises(LexicalError) as err:
            self.lexer.scan(source, trace=True)
        exc = err.exception
        self.assertEqual(source[exc.start:exc.end], "12.")
        self.assertEqual((exc.line, exc.column), (1, 4))

    def test_error_marks_bang(self):
        source = "a! b"
        with self.assertRaises(LexicalError) as err:
            self.lexer.scan(source, trace=True)
        exc = err.exception
        self.assertEqual(source[exc.start:exc.end], "!")

    def test_windows_newlines_one_lexeme(self):
        self.assertEqual([t.lexeme for t in self.lexer.scan("a\r\nb\rc").tokens],
                         ["a", "¶", "b", "¶", "c"])

    def test_csv_export_ukrainian_and_headers(self):
        result = self.lexer.scan("sum:=2\nsum:=sum+2")
        with TemporaryDirectory() as directory:
            paths = export_csv(result, directory)
            self.assertEqual({p.name for p in paths},
                             {"lexemes.csv", "idn.csv", "con.csv"})
            for path in paths:
                self.assertEqual(path.read_bytes()[:3], b"\xef\xbb\xbf")
            with (Path(directory)/"lexemes.csv").open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], ["№", "Рядок", "Лексема", "Код", "Індекс IDN/CON"])
            self.assertEqual(rows[1], ["1", "1", "sum", "37", "1"])
            self.assertEqual(rows[2], ["2", "1", ":=", "20", ""])
            with (Path(directory)/"con.csv").open(encoding="utf-8-sig", newline="") as f:
                self.assertEqual(list(csv.reader(f)), [["Індекс", "Константа"], ["1", "2"]])


if __name__ == "__main__":
    unittest.main()
