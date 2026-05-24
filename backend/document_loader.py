# Load and extract text from PDF and DOCX files.

from pathlib import Path

from pypdf import PdfReader
from docx import Document as DocxDocument


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


# Normalize whitespace and strip noise from extracted text.
def clean_text(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    joined = "\n".join(line for line in lines if line)
    # Collapse multiple spaces within lines
    parts = []
    for line in joined.split("\n"):
        words = line.split()
        parts.append(" ".join(words))
    return "\n\n".join(parts).strip()


def load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages_text: list[str] = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:
            pages_text.append("")
    return clean_text("\n\n".join(pages_text))


def load_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return clean_text("\n\n".join(paragraphs))


# Extract text from a supported file.
#
# Raises:
#     ValueError: If extension is not supported or file is empty.
def load_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}. Use PDF or DOCX.")

    if suffix == ".pdf":
        text = load_pdf(path)
    else:
        text = load_docx(path)

    if not text.strip():
        raise ValueError(f"No extractable text found in {path.name}.")

    return text
