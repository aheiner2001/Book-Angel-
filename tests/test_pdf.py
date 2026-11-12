from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject
from book_angel.parser.pdf_engine import parse_pdf, PdfBook


def create_dummy_pdf(
    path: Path,
    text: str = "",
    title: str | None = "PDF Sample",
    author: str | None = "Author Name",
    num_pages: int = 1,
) -> Path:
    writer = PdfWriter()
    for _ in range(num_pages):
        page = writer.add_blank_page(width=200, height=200)
        if text:
            font_dict = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            font_ref = writer._add_object(font_dict)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})
            })
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 50 150 Td ({text}) Tj ET".encode("latin1"))
            stream_ref = writer._add_object(stream)
            page[NameObject("/Contents")] = stream_ref

    metadata: dict[str, str] = {}
    if title is not None:
        metadata["/Title"] = title
    if author is not None:
        metadata["/Author"] = author
    if metadata:
        writer.add_metadata(metadata)

    with open(path, "wb") as f:
        writer.write(f)
    return path


def test_parse_blank_pdf(tmp_path: Path):
    pdf_path = tmp_path / "blank.pdf"
    create_dummy_pdf(pdf_path, text="")

    book = parse_pdf(pdf_path)
    assert book.title == "PDF Sample"
    assert book.author == "Author Name"
    assert book.page_count == 1
    assert book.is_scanned_or_empty
    assert book.is_scanned
    assert len(book.pages) == 1
    assert book.pages[0] == ""


def test_parse_pdf_with_text(tmp_path: Path):
    pdf_path = tmp_path / "content.pdf"
    create_dummy_pdf(pdf_path, text="Hello Book Angel", title="Sample Book", author="Jane Doe", num_pages=2)

    book = parse_pdf(pdf_path)
    assert book.title == "Sample Book"
    assert book.author == "Jane Doe"
    assert book.page_count == 2
    assert not book.is_scanned_or_empty
    assert not book.is_scanned
    assert len(book.pages) == 2
    assert "Hello Book Angel" in book.pages[0]
    assert "Hello Book Angel" in book.pages[1]


def test_parse_pdf_metadata_fallback(tmp_path: Path):
    pdf_path = tmp_path / "fallback_sample.pdf"
    create_dummy_pdf(pdf_path, text="Some text", title=None, author=None)

    book = parse_pdf(pdf_path)
    assert book.title == "fallback_sample"
    assert book.author == "Unknown"
    assert book.page_count == 1
    assert not book.is_scanned_or_empty


def test_parse_pdf_with_str_path(tmp_path: Path):
    pdf_path = tmp_path / "str_path_test.pdf"
    create_dummy_pdf(pdf_path, text="Testing string path")

    book = parse_pdf(str(pdf_path))
    assert isinstance(book.file_path, Path)
    assert book.title == "PDF Sample"
    assert not book.is_scanned_or_empty


def test_parse_corrupt_pdf(tmp_path: Path):
    corrupt_path = tmp_path / "corrupt.pdf"
    corrupt_path.write_bytes(b"not a valid pdf content")

    book = parse_pdf(corrupt_path)
    assert book.title == "Corrupt PDF"
    assert book.is_scanned_or_empty
    assert book.page_count == 0
    assert book.pages == []
