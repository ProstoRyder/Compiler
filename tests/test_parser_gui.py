import tkinter as tk
import unittest
from gui import LexerGUI


class SyntaxGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = LexerGUI()
            cls.root.withdraw()
        except tk.TclError as exc:
            raise unittest.SkipTest(f'Немає графічного середовища: {exc}')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'root'):
            cls.root.destroy()

    def test_valid_program_and_steps(self):
        self.root.load_example()
        self.root.analyze()
        self.assertIsNone(self.root.syntax_error)
        self.assertTrue(self.root.syntax_steps)
        self.assertEqual(len(self.root.syntax_table.get_children()), len(self.root.syntax_steps))
        self.root.first_syntax_step()
        self.assertEqual(self.root.syntax_step_index, 0)
        self.root.next_syntax_step()
        self.assertEqual(self.root.syntax_step_index, 1)

    def test_invalid_program_error_line(self):
        source = 'program demo\nvar a: integer\nbegin\na := 1 +\nend.'
        self.root._set_editor_text(source)
        self.root.analyze()
        self.assertEqual(self.root.syntax_error.line, 4)
        self.assertIn('Рядок 4', self.root.status_label.cget('text'))
        self.assertTrue(self.root.editor.tag_ranges('lexical_error'))
