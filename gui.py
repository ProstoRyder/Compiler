from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from exporter import FILES, export_csv
from lexer import Lexer, LexerResult, LexicalError, TraceStep
from parser import Parser, SyntaxAnalysisError, ParseStep
from poliz import PolizResult, PolizStep, generate_poliz


HERE = Path(__file__).resolve().parent


class LexerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Компілятор — лабораторна №4. Побудова ПОЛІЗ | Варіант 4")
        self.geometry("1380x790")
        self.minsize(1050, 640)
        self.configure(bg="#f1f5f9")

        self.result: LexerResult | None = None
        self.error: LexicalError | None = None
        self.trace_steps: list[TraceStep] = []
        self.syntax_steps: list[ParseStep] = []
        self.poliz_result: PolizResult | None = None
        self.poliz_steps: list[PolizStep] = []
        self.poliz_step_index = -1
        self.syntax_error: SyntaxAnalysisError | None = None
        self.syntax_step_index = -1
        self.step_index = -1
        self._updating_trace_selection = False

        self._configure_styles()
        self._build_widgets()
        self._setup_shortcuts()
        self.load_example()

    def _configure_styles(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Root.TFrame", background="#f1f5f9")
        style.configure("Pane.TFrame", background="#ffffff")
        style.configure("Heading.TLabel", background="#f1f5f9", foreground="#172554",
                        font=("Segoe UI", 17, "bold"))
        style.configure("Hint.TLabel", background="#f1f5f9", foreground="#475569",
                        font=("Segoe UI", 9))
        style.configure("Status.TLabel", background="#eef2ff", foreground="#1e3a8a",
                        padding=(12, 9), font=("Segoe UI", 10))
        style.configure("Main.TButton", padding=(10, 7), font=("Segoe UI", 10))
        style.configure("TNotebook", background="#ffffff", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 7), font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=25, font=("Consolas", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_widgets(self):
        outer = ttk.Frame(self, style="Root.TFrame", padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Лексичний, синтаксичний аналіз і ПОЛІЗ", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="ЛР №4  •  Варіант №4  •  Лексер → парсер → алгоритм Дейкстри → ПОЛІЗ",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        toolbar = ttk.Frame(outer, style="Root.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        for text, command in (
            ("Відкрити файл", self.open_file),
            ("Тестова програма", self.load_example),
            ("Побудувати ПОЛІЗ", self.analyze),
            ("Експорт CSV", self.export_results),
            ("Зберегти ПОЛІЗ", self.save_poliz),
        ):
            button = ttk.Button(toolbar, text=text, command=command, style="Main.TButton")
            button.pack(side="left", padx=(0, 8))
            if text == "Експорт CSV":
                self.export_button = button
            if text == "Зберегти ПОЛІЗ":
                self.save_poliz_button = button

        main = ttk.Panedwindow(outer, orient="horizontal")
        main.pack(fill="both", expand=True)

        left = ttk.LabelFrame(main, text="  Вихідний текст програми  ", padding=8)
        right = ttk.LabelFrame(main, text="  Результати аналізу  ", padding=8)
        main.add(left, weight=45)
        main.add(right, weight=55)

        edit_frame = ttk.Frame(left)
        edit_frame.pack(fill="both", expand=True)
        self.editor = tk.Text(
            edit_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            background="#ffffff",
            foreground="#0f172a",
            insertbackground="#0f172a",
            padx=10,
            pady=10,
            selectbackground="#bfdbfe",
        )
        self.editor.grid(row=0, column=0, sticky="nsew")
        v_scroll = ttk.Scrollbar(edit_frame, orient="vertical", command=self.editor.yview)
        h_scroll = ttk.Scrollbar(edit_frame, orient="horizontal", command=self.editor.xview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        edit_frame.columnconfigure(0, weight=1)
        edit_frame.rowconfigure(0, weight=1)
        self.editor.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.editor.tag_configure("active_symbol", background="#bfdbfe", foreground="#1d4ed8")
        self.editor.tag_configure("lexical_error", background="#fecaca", foreground="#991b1b", underline=True)
        self.editor.tag_configure("syntax_active", background="#dbeafe", foreground="#1d4ed8")
        self.editor.tag_configure("poliz_active", background="#dcfce7", foreground="#166534")
        self.editor.bind("<<Modified>>", self._on_editor_modified)
        self.editor.edit_modified(False)

        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self.token_table = self._make_tab(
            "Лексеми", ("num", "line", "lexeme", "code", "index"),
            ("№", "Рядок", "Лексема", "Код", "IDN / CON"),
            (54, 70, 165, 65, 92),
        )
        self.idn_table = self._make_tab("IDN", ("index", "identifier"),
                                        ("Індекс", "Ідентифікатор"), (90, 270))
        self.con_table = self._make_tab("CON", ("index", "constant"),
                                        ("Індекс", "Константа"), (90, 270))
        self.trace_table = self._make_tab(
            "Переходи", ("num", "state", "symbol", "target", "action"),
            ("Крок", "Стан", "Символ", "Далі", "Дія"),
            (65, 75, 80, 80, 330),
        )
        self.trace_table.bind("<<TreeviewSelect>>", self._on_trace_select)
        self.syntax_table = self._make_tab(
            "Синтаксис", ("num", "line", "token", "rule", "action", "stack"),
            ("Крок", "Рядок", "Лексема", "Правило", "Дія", "Стек викликів"),
            (60, 65, 90, 145, 270, 330),
        )
        self.syntax_table.bind("<<TreeviewSelect>>", self._on_syntax_select)
        self._build_poliz_tab()
        syntax_controls = ttk.Frame(right)
        syntax_controls.pack(fill="x", pady=(6, 0))
        for label, func in (("|< Синтаксис", self.first_syntax_step),
                            ("< Назад", self.previous_syntax_step),
                            ("Далі >", self.next_syntax_step),
                            ("Синтаксис >|", self.last_syntax_step)):
            ttk.Button(syntax_controls, text=label, command=func).pack(side="left", padx=(0, 5))

        controls = ttk.Frame(outer, style="Root.TFrame")
        controls.pack(fill="x", pady=(10, 5))
        for text, command in (
            ("|<", self.first_step),
            ("< Назад", self.previous_step),
            ("Далі >", self.next_step),
            (">|", self.last_step),
            ("Усі результати", self.show_all),
        ):
            ttk.Button(controls, text=text, command=command, style="Main.TButton").pack(
                side="left", padx=(0, 7))
        self.step_label = ttk.Label(controls, text="Кроки не завантажено", style="Hint.TLabel")
        self.step_label.pack(side="left", padx=(12, 0))

        self.status_label = ttk.Label(outer, text="Завантажте або введіть програму та натисніть «Аналізувати»",
                                      style="Status.TLabel", anchor="w")
        self.status_label.pack(fill="x")
        self.export_button.configure(state="disabled")
        self.save_poliz_button.configure(state="disabled")

    def _build_poliz_tab(self):
        self.poliz_page = ttk.Frame(self.tabs, padding=5)
        self.tabs.add(self.poliz_page, text="ПОЛІЗ")
        ttk.Label(self.poliz_page, text="ПОЛІЗ (повний запис або стан на обраному кроці):").pack(anchor="w")
        self.poliz_output = tk.Text(self.poliz_page, height=6, font=("Consolas", 10),
                                    wrap="word", background="#f8fafc", state="disabled", padx=8, pady=6)
        self.poliz_output.pack(fill="x", pady=(3, 8))
        table_container = ttk.Frame(self.poliz_page)
        table_container.pack(fill="both", expand=True)
        self.poliz_table = ttk.Treeview(table_container,
            columns=("num", "line", "token", "stack", "output", "action"),
            show="headings", selectmode="browse")
        for key, label, width in (
            ("num", "№", 40), ("line", "Рядок", 54), ("token", "Вхідна лексема", 112),
            ("stack", "Стек операторів", 145), ("output", "Вихідний ПОЛІЗ", 260),
            ("action", "Дія", 165),
        ):
            self.poliz_table.heading(key, text=label)
            self.poliz_table.column(key, width=width, minwidth=45, anchor="w")
        self.poliz_table.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(table_container, orient="vertical", command=self.poliz_table.yview)
        xscroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.poliz_table.xview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.poliz_table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        table_container.columnconfigure(0, weight=1)
        table_container.rowconfigure(0, weight=1)
        self.poliz_table.bind("<<TreeviewSelect>>", self._on_poliz_select)
        nav = ttk.Frame(self.poliz_page)
        nav.pack(fill="x", pady=(8, 0))
        for label, action in (("|<", self.first_poliz_step),
                              ("< Назад", self.previous_poliz_step),
                              ("Далі >", self.next_poliz_step),
                              (">|", self.last_poliz_step),
                              ("Весь ПОЛІЗ", self.show_full_poliz)):
            ttk.Button(nav, text=label, command=action).pack(side="left", padx=(0, 5))
        self.poliz_step_label = ttk.Label(nav, text="Немає кроків", style="Hint.TLabel")
        self.poliz_step_label.pack(side="left", padx=(8, 0))

    def _make_tab(self, title, columns, headers, widths) -> ttk.Treeview:
        page = ttk.Frame(self.tabs, padding=3)
        self.tabs.add(page, text=title)
        table = ttk.Treeview(page, columns=columns, show="headings", selectmode="browse")
        for key, label, width in zip(columns, headers, widths):
            table.heading(key, text=label)
            table.column(key, width=width, minwidth=50,
                         anchor="w" if key in ("lexeme", "identifier", "constant", "action") else "center",
                         stretch=key in ("lexeme", "identifier", "constant", "action"))
        table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=table.yview)
        scrollbar.pack(side="right", fill="y")
        table.configure(yscrollcommand=scrollbar.set)
        return table

    def _setup_shortcuts(self):
        self.bind("<Control-o>", lambda event: self.open_file())
        self.bind("<Control-Return>", lambda event: self.analyze())
        self.bind("<Control-e>", lambda event: self.export_results())

    def _on_editor_modified(self, _event):
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        if self.result is not None or self.trace_steps or self.syntax_steps or self.poliz_steps:
            self._clear_previous_result()
            self.status_label.configure(text="Вихідний код змінено. Натисніть «Аналізувати» повторно.")

    def _set_editor_text(self, source: str):
        source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", source)
        self.editor.edit_modified(False)
        self._clear_previous_result()

    def load_example(self):
        path = HERE / "examples" / "valid.txt"
        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            messagebox.showerror("Приклад недоступний", str(exc))
            return
        self._set_editor_text(source)
        self.status_label.configure(text=f"Завантажено приклад: {path.name}. Натисніть «Аналізувати».")

    def open_file(self):
        filename = filedialog.askopenfilename(
            title="Відкрити програму",
            filetypes=[("Текстові файли", "*.txt *.src *.lang"), ("Усі файли", "*.*")],
        )
        if not filename:
            return
        try:
            source = Path(filename).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Помилка відкриття", str(exc))
            return
        self._set_editor_text(source)
        self.status_label.configure(text=f"Завантажено: {filename}")

    def _clear_previous_result(self):
        self.result = None
        self.error = None
        self.trace_steps = []
        self.syntax_steps = []
        self.syntax_error = None
        self.poliz_result = None
        self.poliz_steps = []
        self.poliz_step_index = -1
        self.syntax_step_index = -1
        self.step_index = -1
        self.editor.tag_remove("lexical_error", "1.0", "end")
        self.editor.tag_remove("active_symbol", "1.0", "end")
        self.editor.tag_remove("syntax_active", "1.0", "end")
        self.editor.tag_remove("poliz_active", "1.0", "end")
        for table in (self.token_table, self.idn_table, self.con_table, self.trace_table, self.syntax_table, self.poliz_table):
            table.delete(*table.get_children())
        self.export_button.configure(state="disabled")
        self.save_poliz_button.configure(state="disabled")
        self._set_poliz_output("")
        self.poliz_step_label.configure(text="Немає кроків")
        self.step_label.configure(text="Немає результату")

    def analyze(self):
        source = self.editor.get("1.0", "end-1c")
        self._clear_previous_result()
        try:
            self.result = Lexer().scan(source, trace=True)
        except LexicalError as error:
            self.error = error
            self.result = error.partial_result
            self.trace_steps = self.result.steps if self.result else []
            self._fill_trace()
            self._fill_tables()
            self._highlight_error()
            self.status_label.configure(text=f"ЛЕКСИЧНА ПОМИЛКА: {error}")
            self.step_label.configure(text=f"{len(self.trace_steps)} переходів до помилки")
            self.tabs.select(self.trace_table.master)
            return

        self.trace_steps = self.result.steps
        self._fill_trace()
        self._fill_tables()
        self.export_button.configure(state="normal")
        self.step_label.configure(text=f"{len(self.trace_steps)} переходів; кнопка «Далі >» — покроковий режим")
        self.tabs.select(0)
        parser = Parser(self.result.tokens)
        try:
            parser.parse()
        except SyntaxAnalysisError as exc:
            self.syntax_error = exc
        self.syntax_steps = parser.steps
        self._fill_syntax_trace()
        self.tabs.select(self.syntax_table.master)
        if self.syntax_error is not None:
            self._highlight_syntax_line(self.syntax_error.line)
            self.status_label.configure(text=f"СИНТАКСИЧНА ПОМИЛКА: {self.syntax_error}")
        else:
            # Генератор викликається лише після успішного Parser.parse().
            try:
                self.poliz_result = generate_poliz(self.result.tokens, validate=False)
            except Exception as exc:
                self.status_label.configure(text=f"ПОМИЛКА ГЕНЕРАЦІЇ ПОЛІЗ: {exc}")
                return
            self.poliz_steps = list(self.poliz_result.steps)
            self._fill_poliz_trace()
            self._set_poliz_output(self.poliz_result.text)
            self.save_poliz_button.configure(state="normal")
            self.tabs.select(self.poliz_page)
            self.poliz_step_label.configure(text=f"{len(self.poliz_steps)} кроків")
            self.status_label.configure(
                text=f"Успішно: {len(self.result.tokens)} лексем; "
                     f"{len(self.syntax_steps)} кроків парсера; "
                     f"{len(self.poliz_steps)} кроків ПОЛІЗ; "
                     f"{len(self.poliz_result.code)} елементів вихідного запису."
            )

    def _set_poliz_output(self, content: str):
        self.poliz_output.configure(state="normal")
        self.poliz_output.delete("1.0", "end")
        self.poliz_output.insert("1.0", content)
        self.poliz_output.configure(state="disabled")

    def _fill_poliz_trace(self):
        self.poliz_table.delete(*self.poliz_table.get_children())
        for i, step in enumerate(self.poliz_steps):
            self.poliz_table.insert("", "end", iid=f"poliz-{i}", values=(
                step.number, step.line, step.lexeme,
                " ".join(step.operator_stack) or "—",
                " ".join(step.output), step.action,
            ))

    def go_to_poliz_step(self, index: int):
        if not self.poliz_steps:
            return
        index = max(0, min(index, len(self.poliz_steps) - 1))
        self.poliz_step_index = index
        step = self.poliz_steps[index]
        self._set_poliz_output(" ".join(step.output))
        self.editor.tag_remove("poliz_active", "1.0", "end")
        if step.token_index is not None:
            self.editor.tag_add("poliz_active", f"{step.line}.0", f"{step.line}.end")
            self.editor.see(f"{step.line}.0")
        iid = f"poliz-{index}"
        if self.poliz_table.selection() != (iid,):
            self.poliz_table.selection_set(iid)
        self.poliz_table.focus(iid)
        self.poliz_table.see(iid)
        self.poliz_step_label.configure(text=f"Крок {index + 1}/{len(self.poliz_steps)}")

    def _on_poliz_select(self, _event):
        selected = self.poliz_table.selection()
        if selected:
            index = int(selected[0].split("-")[1])
            if index != self.poliz_step_index:
                self.go_to_poliz_step(index)

    def first_poliz_step(self):
        self.go_to_poliz_step(0)

    def previous_poliz_step(self):
        self.go_to_poliz_step(self.poliz_step_index - 1)

    def next_poliz_step(self):
        self.go_to_poliz_step(self.poliz_step_index + 1)

    def last_poliz_step(self):
        self.go_to_poliz_step(len(self.poliz_steps) - 1)

    def show_full_poliz(self):
        if self.poliz_result is None:
            return
        self.poliz_step_index = -1
        self._set_poliz_output(self.poliz_result.text)
        self.editor.tag_remove("poliz_active", "1.0", "end")
        for iid in self.poliz_table.selection():
            self.poliz_table.selection_remove(iid)
        self.poliz_step_label.configure(text=f"Весь ПОЛІЗ ({len(self.poliz_result.code)} елементів)")

    def save_poliz(self):
        if self.poliz_result is None:
            messagebox.showinfo("Немає результату", "Спочатку побудуйте ПОЛІЗ.")
            return
        filename = filedialog.asksaveasfilename(title="Зберегти ПОЛІЗ", defaultextension=".txt",
            filetypes=[("Текстові файли", "*.txt"), ("Усі файли", "*.*")],
            initialfile="poliz.txt")
        if not filename:
            return
        try:
            Path(filename).write_text(self.poliz_result.text + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Помилка збереження", str(exc))
        else:
            messagebox.showinfo("Готово", f"ПОЛІЗ збережено: {filename}")

    def _fill_syntax_trace(self):
        self.syntax_table.delete(*self.syntax_table.get_children())
        for index, step in enumerate(self.syntax_steps):
            self.syntax_table.insert("", "end", iid=f"syntax-{index}", values=(
                step.number, step.line, step.token, step.rule, step.action, step.stack,
            ))

    def _highlight_syntax_line(self, line: int):
        self.editor.tag_remove("lexical_error", "1.0", "end")
        self.editor.tag_add("lexical_error", f"{line}.0", f"{line}.end")
        self.editor.see(f"{line}.0")

    def go_to_syntax_step(self, index: int):
        if not self.syntax_steps:
            return
        index = max(0, min(index, len(self.syntax_steps) - 1))
        self.syntax_step_index = index
        step = self.syntax_steps[index]
        self.editor.tag_remove("syntax_active", "1.0", "end")
        self.editor.tag_add("syntax_active", f"{step.line}.0", f"{step.line}.end")
        self.editor.see(f"{step.line}.0")
        self.syntax_table.selection_set(f"syntax-{index}")
        self.syntax_table.focus(f"syntax-{index}")
        self.syntax_table.see(f"syntax-{index}")
        self.step_label.configure(text=f"Синтаксис: крок {index+1}/{len(self.syntax_steps)} | {step.rule} | {step.action}")

    def _on_syntax_select(self, _event):
        selection = self.syntax_table.selection()
        if selection:
            index = int(selection[0].split("-")[1])
            if index != self.syntax_step_index:
                self.go_to_syntax_step(index)

    def first_syntax_step(self):
        self.go_to_syntax_step(0)

    def previous_syntax_step(self):
        self.go_to_syntax_step(self.syntax_step_index - 1)

    def next_syntax_step(self):
        self.go_to_syntax_step(self.syntax_step_index + 1)

    def last_syntax_step(self):
        self.go_to_syntax_step(len(self.syntax_steps) - 1)

    def _fill_tables(self, step: TraceStep | None = None):
        if not self.result:
            return
        for table in (self.token_table, self.idn_table, self.con_table):
            table.delete(*table.get_children())
        tokens = self.result.tokens[:step.token_count] if step else self.result.tokens
        idns = self.result.idn[:step.idn_count] if step else self.result.idn
        cons = self.result.con[:step.con_count] if step else self.result.con
        for n, token in enumerate(tokens, 1):
            self.token_table.insert("", "end", values=(
                n, token.line, token.lexeme, token.code,
                token.index if token.index is not None else "—",
            ))
        for n, identifier in enumerate(idns, 1):
            self.idn_table.insert("", "end", values=(n, identifier))
        for n, constant in enumerate(cons, 1):
            self.con_table.insert("", "end", values=(n, constant))

    def _fill_trace(self):
        self.trace_table.delete(*self.trace_table.get_children())
        for step in self.trace_steps:
            self.trace_table.insert("", "end", iid=str(step.number - 1), values=(
                step.number, step.state, step.symbol, step.next_state, step.action,
            ))

    def _mark_range(self, tag: str, start: int, end: int):
        pos1 = f"1.0+{start}c"
        pos2 = f"1.0+{max(start + 1, end)}c"
        self.editor.tag_add(tag, pos1, pos2)
        self.editor.see(pos1)

    def _highlight_error(self):
        self.editor.tag_remove("lexical_error", "1.0", "end")
        if self.error:
            self._mark_range("lexical_error", self.error.start, self.error.end)
            self.editor.tag_raise("lexical_error")

    def go_to_step(self, index: int):
        if not self.trace_steps:
            return
        index = max(0, min(index, len(self.trace_steps) - 1))
        self.step_index = index
        step = self.trace_steps[index]
        self._fill_tables(step)
        self.editor.tag_remove("active_symbol", "1.0", "end")
        if step.start < step.end:
            self._mark_range("active_symbol", step.start, step.end)
        self._highlight_error()
        self.step_label.configure(
            text=f"Крок {index + 1}/{len(self.trace_steps)} | "
                 f"{step.state} → {step.next_state} | Рядок {step.line}:{step.column}"
        )
        if not self.error:
            self.status_label.configure(text=step.action)
        self._updating_trace_selection = True
        try:
            if tuple(self.trace_table.selection()) != (str(index),):
                self.trace_table.selection_set(str(index))
            self.trace_table.focus(str(index))
            self.trace_table.see(str(index))
        finally:
            self._updating_trace_selection = False

    def _on_trace_select(self, _event):
        if self._updating_trace_selection:
            return
        selected = self.trace_table.selection()
        if selected and int(selected[0]) != self.step_index:
            self.go_to_step(int(selected[0]))

    def first_step(self):
        self.go_to_step(0)

    def previous_step(self):
        if self.trace_steps:
            self.go_to_step(self.step_index - 1 if self.step_index >= 0 else len(self.trace_steps) - 1)

    def next_step(self):
        if self.trace_steps:
            self.go_to_step(self.step_index + 1)

    def last_step(self):
        self.go_to_step(len(self.trace_steps) - 1)

    def show_all(self):
        if not self.result:
            return
        self.step_index = -1
        self.editor.tag_remove("active_symbol", "1.0", "end")
        self._highlight_error()
        self._fill_tables()
        self._updating_trace_selection = True
        try:
            for iid in self.trace_table.selection():
                self.trace_table.selection_remove(iid)
        finally:
            self._updating_trace_selection = False
        self.step_label.configure(text=f"Усі результати ({len(self.trace_steps)} переходів)")
        if self.error:
            self.status_label.configure(text=f"ЛЕКСИЧНА ПОМИЛКА: {self.error}")
        else:
            self.status_label.configure(text=f"Всього лексем: {len(self.result.tokens)}; "
                                             f"IDN: {len(self.result.idn)}; CON: {len(self.result.con)}")

    def export_results(self):
        if self.result is None or self.error is not None:
            messagebox.showinfo("Немає результатів", "Спочатку успішно виконайте лексичний аналіз.")
            return
        selected = filedialog.askdirectory(title="Оберіть папку для CSV")
        if not selected:
            return
        target = Path(selected)
        existing = [name for name in FILES if (target / name).exists()]
        if existing and not messagebox.askyesno(
            "Підтвердження",
            "У папці вже існують файли: " + ", ".join(existing) + ". Замінити їх?",
        ):
            return
        try:
            paths = export_csv(self.result, target)
        except OSError as exc:
            messagebox.showerror("Помилка експорту", str(exc))
            return
        messagebox.showinfo("Експорт виконано", "Збережено:\n" + "\n".join(str(p) for p in paths))


def main():
    app = LexerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
