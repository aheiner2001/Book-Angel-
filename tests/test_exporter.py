from pathlib import Path
import zipfile
import pytest
from book_angel.exporter import export_book
from book_angel.staging import StagingWorkspace
from book_angel.parser.chunker import BookChunk
from book_angel.config import RulesConfig
from book_angel.parser.epub_engine import parse_epub
from book_angel.parser.pdf_engine import parse_pdf


def test_export_epub(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="export-test")
    ws.initialize(
        title="Original Title",
        author="Original Author",
        cover_bytes=b"MYCOVER",
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Pristine paragraph.")
        ]
    )

    out_dir = tmp_path / "dist"
    out_file = export_book(
        workspace=ws,
        output_dir=out_dir,
        export_format="epub",
        title_suffix="[Clean Edition]"
    )

    assert out_file.exists()
    assert out_file.suffix == ".epub"

    # Verify zip integrity and cover presence
    with zipfile.ZipFile(out_file, "r") as zf:
        assert "mimetype" in zf.namelist()
        assert "OEBPS/content.opf" in zf.namelist()
        assert "OEBPS/images/cover.jpg" in zf.namelist()
        opf_data = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "Original Title [Clean Edition]" in opf_data

    # Verify readable by parse_epub
    book = parse_epub(out_file)
    assert book.title == "Original Title [Clean Edition]"
    assert book.author == "Original Author"
    assert book.cover_bytes == b"MYCOVER"
    book.close()


def test_export_epub_without_cover(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="no-cover-test")
    ws.initialize(
        title="No Cover Book",
        author="Coverless Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Text without cover.")
        ]
    )

    out_dir = tmp_path / "dist"
    out_file = export_book(
        workspace=ws,
        output_dir=out_dir,
        export_format="epub",
    )

    assert out_file.exists()
    with zipfile.ZipFile(out_file, "r") as zf:
        assert "OEBPS/images/cover.jpg" not in zf.namelist()
        opf_data = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "No Cover Book" in opf_data
        assert "cover-image" not in opf_data


def test_export_pdf(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="pdf-export-test")
    ws.initialize(
        title="PDF Book",
        author="PDF Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="PDF content paragraph.")
        ]
    )

    out_dir = tmp_path / "dist"
    out_file = export_book(
        workspace=ws,
        output_dir=out_dir,
        export_format="pdf",
        title_suffix="Clean"
    )

    assert out_file.exists()
    assert out_file.suffix == ".pdf"

    # Verify readable by parse_pdf
    pdf_book = parse_pdf(out_file)
    assert pdf_book.title == "PDF Book Clean"
    assert pdf_book.author == "PDF Author"
    assert pdf_book.page_count >= 1


def test_export_custom_title_overrides_suffix(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="custom-title-test")
    ws.initialize(
        title="Default Title",
        author="Some Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Some body.")
        ]
    )

    out_dir = tmp_path / "dist"
    out_file = export_book(
        workspace=ws,
        output_dir=out_dir,
        export_format="epub",
        title_suffix="[Clean Edition]",
        custom_title="Custom Override Title"
    )

    with zipfile.ZipFile(out_file, "r") as zf:
        opf_data = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "Custom Override Title" in opf_data
        assert "[Clean Edition]" not in opf_data


def test_export_multiple_chunks_assembled_in_order(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="multi-chunk-test")
    ws.initialize(
        title="Multi Chapter",
        author="Multi Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="First paragraph."),
            BookChunk(chunk_id=2, chapter_idx=1, scene_idx=2, chapter_title="Ch 1", body="Second paragraph."),
            BookChunk(chunk_id=10, chapter_idx=2, scene_idx=1, chapter_title="Ch 2", body="Tenth paragraph."),
        ]
    )

    # Edit chunk 2 in workspace
    (ws.chunks_dir / "chunk_002.txt").write_text(
        "<!-- chunk_id: 002 | chapter: 1 | scene: 2 | title: Ch 1 -->\n\nSecond modified paragraph.",
        encoding="utf-8"
    )

    # Add a non-digit file that should be ignored
    (ws.chunks_dir / "chunk_backup.txt").write_text("Ignore this backup file", encoding="utf-8")

    out_dir = tmp_path / "dist"
    out_file = export_book(workspace=ws, output_dir=str(out_dir), export_format="epub")

    with zipfile.ZipFile(out_file, "r") as zf:
        xhtml_data = zf.read("OEBPS/chapter1.xhtml").decode("utf-8")
        assert "First paragraph." in xhtml_data
        assert "Second modified paragraph." in xhtml_data
        assert "Tenth paragraph." in xhtml_data
        assert "Ignore this backup file" not in xhtml_data
        # Ensure metadata headers are stripped
        assert "<!-- chunk_id" not in xhtml_data
        # Check ordering
        idx1 = xhtml_data.find("First paragraph.")
        idx2 = xhtml_data.find("Second modified paragraph.")
        idx10 = xhtml_data.find("Tenth paragraph.")
        assert idx1 < idx2 < idx10


def test_export_safe_slug_with_special_characters(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="slug-test")
    ws.initialize(
        title="What's Up: Volume #1?!",
        author="Special Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Content.")
        ]
    )

    out_dir = tmp_path / "dist"
    out_file = export_book(workspace=ws, output_dir=out_dir, export_format="epub")

    assert out_file.exists()
    assert "/" not in out_file.name
    assert ":" not in out_file.name
    assert "?" not in out_file.name
    assert "#" not in out_file.name


def test_export_epub_apple_books_compatibility(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="apple-books-test")
    ws.initialize(
        title="Apple Books Guide",
        author="Apple Author",
        cover_bytes=b"FAKECOVERIMAGE",
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Introduction", body="Opening content &nbsp; with entity.")
        ]
    )

    out_dir = tmp_path / "apple_dist"
    out_file = export_book(workspace=ws, output_dir=out_dir, export_format="epub")

    assert out_file.exists()
    with zipfile.ZipFile(out_file, "r") as zf:
        infolist = zf.infolist()
        # 1. First file must be uncompressed mimetype
        assert infolist[0].filename == "mimetype"
        assert infolist[0].compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"

        # 2. Must contain Apple Books mandatory files
        assert "META-INF/container.xml" in zf.namelist()
        assert "OEBPS/nav.xhtml" in zf.namelist()
        assert "OEBPS/toc.ncx" in zf.namelist()
        assert "OEBPS/style.css" in zf.namelist()

        # 3. Content.opf validations
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
        assert 'properties="nav"' in opf
        assert "<dc:language>en</dc:language>" in opf
        assert "dcterms:modified" in opf
        assert '<spine toc="ncx">' in opf

        # 4. XML compliance: unescaped &nbsp; replaced with &#160;
        ch1 = zf.read("OEBPS/chapter1.xhtml").decode("utf-8")
        assert "&nbsp;" not in ch1
        assert "&#160;" in ch1


def test_export_patched_source_epub(tmp_path: Path):
    from tests.test_epub import create_dummy_epub

    src_epub = create_dummy_epub(tmp_path / "source.epub")
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="patch-test")
    ws.initialize(
        title="Source Book",
        author="Source Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="ch1", body="Hello world chapter text.")
        ],
        source_file=src_epub,
        chapter_map={"1": {"idref": "ch1", "href": "ch1.xhtml", "archive_path": "OEBPS/ch1.xhtml"}},
    )

    # Edit chunk in workspace
    (ws.chunks_dir / "chunk_001.txt").write_text(
        "<!-- chunk_id: 001 | chapter: 1 | scene: 1 | title: ch1 -->\n\nReplaced clean text for chapter 1.",
        encoding="utf-8"
    )

    out_dir = tmp_path / "patched_dist"
    out_file = export_book(workspace=ws, output_dir=out_dir, export_format="epub", title_suffix="[Clean Edition]")

    assert out_file.exists()
    book = parse_epub(out_file)
    assert book.title == "Source Book [Clean Edition]"
    assert "Replaced clean text for chapter 1." in book.chapters[0].content
    book.close()

