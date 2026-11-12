"""PDF parsing and text extraction engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from pypdf import PdfReader


@dataclass
class PdfBook:
    file_path: Path
    title: str = "Untitled PDF"
    author: str = "Unknown"
    page_count: int = 0
    pages: list[str] = field(default_factory=list)
    is_scanned_or_empty: bool = False

    @property
    def is_scanned(self) -> bool:
        """Alias for is_scanned_or_empty."""
        return self.is_scanned_or_empty


def parse_pdf(path: Path | str) -> PdfBook:
    """Parse a PDF file into a PdfBook dataclass."""
    path = Path(path)
    try:
        reader = PdfReader(str(path))
        meta = reader.metadata or {}
        title = (meta.title if getattr(meta, "title", None) else None) or path.stem or "Untitled PDF"
        author = (meta.author if getattr(meta, "author", None) else None) or "Unknown"

        pages: list[str] = []
        total_text = ""
        for page in reader.pages:
            extracted = page.extract_text() or ""
            pages.append(extracted)
            total_text += extracted.strip()

        return PdfBook(
            file_path=path,
            title=title,
            author=author,
            page_count=len(reader.pages),
            pages=pages,
            is_scanned_or_empty=(len(total_text) == 0),
        )
    except Exception:
        return PdfBook(
            file_path=path,
            title="Corrupt PDF",
            is_scanned_or_empty=True,
        )
