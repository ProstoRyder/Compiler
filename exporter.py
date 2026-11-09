from __future__ import annotations

import csv
from pathlib import Path
from lexer import LexerResult


FILES = ("lexemes.csv", "idn.csv", "con.csv")


def export_csv(result: LexerResult, folder: str | Path) -> list[Path]:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = [folder / name for name in FILES]
    tables = [
        (["№", "Рядок", "Лексема", "Код", "Індекс IDN/CON"],
         [(n, t.line, t.lexeme, t.code, t.index if t.index is not None else "")
          for n, t in enumerate(result.tokens, 1)]),
        (["Індекс", "Ідентифікатор"], list(enumerate(result.idn, 1))),
        (["Індекс", "Константа"], list(enumerate(result.con, 1))),
    ]
    for path, (header, rows) in zip(paths, tables):
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    return paths
