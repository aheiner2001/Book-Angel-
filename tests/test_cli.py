"""Tests for the Book-Angel CLI interface."""
from pathlib import Path
import pytest
import zipfile
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject

from book_angel.cli import create_parser, main
from book_angel.config import RulesConfig
from book_angel.parser.chunker import BookChunk
from book_angel.staging import StagingWorkspace


def create_dummy_epub(path: Path, encrypted: bool = False) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )
        if encrypted:
            zf.writestr("META-INF/encryption.xml", "<encryption/>")

        opf_content = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test EPUB Book</dc:title>
    <dc:creator>Author Person</dc:creator>
  </metadata>
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
  </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", opf_content)
        zf.writestr("OEBPS/ch1.xhtml", "<html><body><p>Hello world chapter text.</p></body></html>")
    return path


def create_dummy_pdf(path: Path, text: str = "") -> Path:
    writer = PdfWriter()
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

    writer.add_metadata({"/Title": "Test PDF Book", "/Author": "PDF Author"})
    with open(path, "wb") as f:
        writer.write(f)
    return path


def test_cli_parser_commands():
    parser = create_parser()
    args = parser.parse_args(["unpack", "book.epub"])
    assert args.command == "unpack"
    assert args.file == "book.epub"

    args_review = parser.parse_args(["review"])
    assert args_review.command == "review"

    args_export = parser.parse_args(["export", "--format", "epub"])
    assert args_export.command == "export"
    assert args_export.format == "epub"

    args_config = parser.parse_args(["config"])
    assert args_config.command == "config"

    args_status = parser.parse_args(["status"])
    assert args_status.command == "status"


def test_cli_config_command(tmp_path, monkeypatch, capsys):
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    main(["config"])

    captured = capsys.readouterr()
    assert "Book-Angel Configuration Wizard" in captured.out
    assert "Rules saved to" in captured.out

    config_path = fake_home / ".book-angel" / "rules.yaml"
    assert config_path.exists()
    assert "romance_level: mild" in config_path.read_text(encoding="utf-8")


def test_cli_unpack_epub_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    epub_path = create_dummy_epub(tmp_path / "my_story.epub")

    main(["unpack", str(epub_path)])

    captured = capsys.readouterr()
    assert "Successfully unpacked" in captured.out

    staging_dir = tmp_path / ".book-angel" / "staging" / "my_story"
    assert staging_dir.exists()
    assert (staging_dir / "meta.json").exists()
    chunks = list((staging_dir / "chunks").glob("chunk_*.txt"))
    assert len(chunks) >= 1


def test_cli_unpack_epub_drm(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    epub_path = create_dummy_epub(tmp_path / "locked.epub", encrypted=True)

    with pytest.raises(SystemExit) as exc_info:
        main(["unpack", str(epub_path)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "DRM-protected" in captured.err


def test_cli_unpack_pdf_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    pdf_path = create_dummy_pdf(tmp_path / "sample.pdf", text="Sample PDF content here.")

    main(["unpack", str(pdf_path)])

    captured = capsys.readouterr()
    assert "Successfully unpacked" in captured.out

    staging_dir = tmp_path / ".book-angel" / "staging" / "sample"
    assert staging_dir.exists()
    assert (staging_dir / "meta.json").exists()
    chunks = list((staging_dir / "chunks").glob("chunk_*.txt"))
    assert len(chunks) >= 1


def test_cli_unpack_pdf_scanned_or_empty(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    pdf_path = create_dummy_pdf(tmp_path / "empty.pdf", text="")

    with pytest.raises(SystemExit) as exc_info:
        main(["unpack", str(pdf_path)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "OCR required" in captured.err


def test_cli_unpack_file_not_found(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(["unpack", "does_not_exist.epub"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "File not found" in captured.err


def test_cli_unpack_unsupported_format(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    txt_file = tmp_path / "book.txt"
    txt_file.write_text("Hello", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(["unpack", str(txt_file)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Unsupported file format" in captured.err


def test_cli_review_no_staging(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    main(["review"])

    captured = capsys.readouterr()
    assert "No active book staging found." in captured.out


def test_cli_review_no_modified_chunks(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="demo-book")
    chunks = [
        BookChunk(
            chunk_id=1,
            chapter_idx=1,
            scene_idx=1,
            chapter_title="Chapter 1",
            body="Initial unmodified text.",
        )
    ]
    ws.initialize("Demo Book", "Author", None, RulesConfig(), chunks)

    main(["review"])

    captured = capsys.readouterr()
    assert "No modified chunks to review. All chunks match original." in captured.out


def test_cli_review_with_modified_chunks(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="demo-book")
    chunks = [
        BookChunk(
            chunk_id=1,
            chapter_idx=1,
            scene_idx=1,
            chapter_title="Chapter 1",
            body="Initial unmodified text.",
        )
    ]
    ws.initialize("Demo Book", "Author", None, RulesConfig(), chunks)

    # Modify chunk in chunks/
    chunk_file = ws.chunks_dir / "chunk_001.txt"
    chunk_file.write_text("Modified text with replacements.", encoding="utf-8")

    main(["review"])

    captured = capsys.readouterr()
    assert "Found 1 modified chunk(s) for review:" in captured.out
    assert "--- Chunk 001 ---" in captured.out
    assert "-Initial unmodified text." in captured.out
    assert "+Modified text with replacements." in captured.out


def test_cli_export_no_staging(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(["export"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "No active book staging found." in captured.err


def test_cli_export_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="export-book")
    chunks = [
        BookChunk(
            chunk_id=1,
            chapter_idx=1,
            scene_idx=1,
            chapter_title="Chapter 1",
            body="Exported paragraph text.",
        )
    ]
    ws.initialize("My Book", "Famous Author", None, RulesConfig(), chunks)

    out_dir = tmp_path / "output"
    main(["export", "--format", "epub", "--out", str(out_dir), "--suffix", "[Clean]"])

    captured = capsys.readouterr()
    assert "Export complete:" in captured.out
    exported_epub = out_dir / "My_Book__Clean.epub"
    assert exported_epub.exists()


def test_cli_status_no_staging(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    main(["status"])

    captured = capsys.readouterr()
    assert "No active staging workspaces." in captured.out


def test_cli_status_with_workspaces(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ws1 = StagingWorkspace(base_dir=tmp_path, book_slug="book-a")
    ws1.initialize("Book A", "Author A", None, RulesConfig(), [
        BookChunk(1, 1, 1, "Ch1", "Text A")
    ])

    ws2 = StagingWorkspace(base_dir=tmp_path, book_slug="book-b")
    ws2.initialize("Book B", "Author B", None, RulesConfig(), [
        BookChunk(1, 1, 1, "Ch1", "Text B")
    ])
    # Modify ws2
    (ws2.chunks_dir / "chunk_001.txt").write_text("Modified B", encoding="utf-8")

    main(["status"])

    captured = capsys.readouterr()
    assert "Workspace: book-a | Modified Chunks: 0" in captured.out
    assert "Workspace: book-b | Modified Chunks: 1" in captured.out
