import tkinter as tk
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from gui import LexerGUI


class PolizGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = LexerGUI()
            cls.root.withdraw()
        except tk.TclError as exc:
            raise unittest.SkipTest(f'Немає графічного дисплея: {exc}')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'root'):
            cls.root.destroy()

    def test_full_example_and_navigation(self):
        self.root.load_example()
        self.root.analyze()
        self.assertIsNone(self.root.syntax_error)
        self.assertIsNotNone(self.root.poliz_result)
        self.assertGreater(len(self.root.poliz_result.code), 50)
        self.assertEqual(len(self.root.poliz_table.get_children()), len(self.root.poliz_steps))
        self.root.first_poliz_step()
        self.assertEqual(self.root.poliz_step_index, 0)
        self.root.next_poliz_step()
        self.assertEqual(self.root.poliz_step_index, 1)
        self.root.last_poliz_step()
        self.assertEqual(self.root.poliz_step_index, len(self.root.poliz_steps)-1)
        self.root.show_full_poliz()
        self.assertEqual(self.root.poliz_step_index, -1)
        self.assertIn('УПХ', self.root.poliz_output.get('1.0', 'end'))
        with (TemporaryDirectory() as folder,
              patch('gui.filedialog.asksaveasfilename', return_value=str(Path(folder)/'poliz.txt')),
              patch('gui.messagebox.showinfo')):
            self.root.save_poliz()
            self.assertTrue((Path(folder)/'poliz.txt').read_text(encoding='utf-8'))

    def test_error_prevents_code_generation(self):
        self.root._set_editor_text('program test\nvar a: integer\nbegin\na := 1 +\nend.')
        self.root.analyze()
        self.assertIsNotNone(self.root.syntax_error)
        self.assertIsNone(self.root.poliz_result)
        self.assertEqual(str(self.root.save_poliz_button['state']), 'disabled')


if __name__ == '__main__':
    unittest.main()
