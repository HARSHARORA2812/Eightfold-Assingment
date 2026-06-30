"""Render docs/technical_design.md into a compact one-page PDF."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "technical_design.md"
OUTPUT = ROOT / "docs" / "technical_design.pdf"


def wrap(line: str, width: int = 104) -> list[str]:
    words = line.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if sum(len(item) for item in current) + len(current) + len(word) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines or [""]


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    c = canvas.Canvas(str(OUTPUT), pagesize=letter)
    text = c.beginText(54, 742)
    text.setFont("Helvetica", 8.6)
    for raw_line in markdown.splitlines():
        line = raw_line.replace("# ", "").replace("`", "")
        if not line.strip():
            text.textLine("")
            continue
        for wrapped in wrap(line):
            text.textLine(wrapped)
    c.drawText(text)
    c.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
