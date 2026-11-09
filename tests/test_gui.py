import tkinter as tk
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from gui import LexerGUI


class GuiTests(unittest.TestCase):
    def test_gui_analyze_step_and_error_highlight(self):
        try:
            window = LexerGUI()
        except tk.TclError as exc:
            self.skipTest(f"Немає графічного дисплея: {exc}")
        try:
            window.withdraw()
            window.analyze()
            self.assertIsNotNone(window.result)
            self.assertIsNone(window.error)
            self.assertEqual(len(window.result.idn), 7)
            self.assertGreater(len(window.trace_steps), 100)
            with TemporaryDirectory() as folder, \
                    patch("gui.filedialog.askdirectory", return_value=folder), \
                    patch("gui.messagebox.showinfo"):
                window.export_results()
                self.assertTrue((Path(folder) / "lexemes.csv").exists())
                self.assertTrue((Path(folder) / "idn.csv").exists())
                self.assertTrue((Path(folder) / "con.csv").exists())
            window.first_step()
            self.assertEqual(window.step_index, 0)
            window.last_step()
            self.assertEqual(window.step_index, len(window.trace_steps) - 1)
            window.show_all()
            self.assertEqual(window.step_index, -1)
            window.editor.insert("end-1c", " ")
            window.update()
            self.assertIsNone(window.result)
            window.analyze()
            self.assertIsNotNone(window.result)
            window._set_editor_text("a := 12.5")
            window.analyze()
            self.assertIsNotNone(window.error)
            self.assertEqual(tuple(map(str, window.editor.tag_ranges("lexical_error"))),
                             ("1.5", "1.8"))
        finally:
            window.destroy()


if __name__ == "__main__":
    unittest.main()
