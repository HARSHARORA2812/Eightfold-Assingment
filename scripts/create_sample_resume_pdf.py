"""Generate samples/resume_sample.pdf for local demos."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "samples" / "resume_sample.pdf"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT), pagesize=letter)
    text = c.beginText(72, 740)
    text.setFont("Helvetica", 11)
    for line in [
        "Ananya Rao",
        "Senior Data Engineer | ananya.rao@example.com | +1 415-555-0134",
        "Location: San Francisco, CA, United States",
        "https://linkedin.com/in/ananyarao | https://github.com/ananyarao",
        "",
        "SKILLS",
        "Python, SQL, Machine Learning, PostgreSQL, Docker",
        "",
        "EXPERIENCE",
        "Senior Data Engineer at Eightfold Labs",
        "Built candidate data pipelines and entity resolution workflows.",
        "Data Engineer at BrightHire",
        "",
        "EDUCATION",
        "M.S. Computer Science, Stanford University, 2020",
    ]:
        text.textLine(line)
    c.drawText(text)
    c.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
