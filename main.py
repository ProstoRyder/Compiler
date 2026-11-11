import sys
from pathlib import Path
from lexer import Lexer, LexicalError
from parser import Parser, SyntaxAnalysisError


def run_cli():
    path = Path(__file__).parent / "examples" / "valid.txt"
    try:
        result = Lexer().scan(path.read_text(encoding="utf-8"))
    except LexicalError as exc:
        print(f"Лексична помилка: {exc}")
        return 1
    print(f"Знайдено лексем: {len(result.tokens)}")
    print("Рядок | Лексема | Код | IDN/CON")
    for token in result.tokens:
        print(f"{token.line:6} | {token.lexeme:12} | {token.code:3} | "
              f"{token.index if token.index is not None else '-'}")
    print("IDN:", result.idn)
    print("CON:", result.con)
    try:
        parser = Parser(result.tokens)
        parser.parse()
    except SyntaxAnalysisError as exc:
        print(f"Синтаксична помилка: {exc}")
        return 2
    print(f"Синтаксис правильний. Кроків розбору: {len(parser.steps)}")
    return 0


if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.exit(run_cli())
    from gui import main
    main()
