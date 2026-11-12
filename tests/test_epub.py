import zipfile
from pathlib import Path
from book_angel.parser.epub_engine import parse_epub, EpubBook, EpubChapter


def create_dummy_epub(path: Path, encrypted: bool = False, epub3_cover: bool = False) -> Path:
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

        if epub3_cover:
            opf_content = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>EPUB3 Test Book</dc:title>
    <dc:creator>EPUB3 Author</dc:creator>
  </metadata>
  <manifest>
    <item id="cover-img" href="images/cover_art.png" media-type="image/png" properties="cover-image"/>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>"""
        else:
            opf_content = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test Book</dc:title>
    <dc:creator>Test Author</dc:creator>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
    <item id="cover-image" href="images/cover.jpg" media-type="image/jpeg"/>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
  </spine>
</package>"""

        zf.writestr("OEBPS/content.opf", opf_content)
        if epub3_cover:
            zf.writestr("OEBPS/images/cover_art.png", b"PNGCOVERBYTES")
            zf.writestr(
                "OEBPS/ch1.xhtml",
                """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body><h1>Chapter 1</h1><p>First chapter content.</p></body>
</html>""",
            )
            zf.writestr(
                "OEBPS/ch2.xhtml",
                """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body><h1>Chapter 2</h1><p>Second chapter content.</p></body>
</html>""",
            )
        else:
            zf.writestr("OEBPS/images/cover.jpg", b"FAKECONTENTCOVER")
            zf.writestr(
                "OEBPS/ch1.xhtml",
                """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
  <h1>Chapter 1</h1>
  <p>The night was cold and damp.</p>
</body>
</html>""",
            )
    return path


def test_parse_valid_epub(tmp_path: Path):
    epub_path = tmp_path / "valid.epub"
    create_dummy_epub(epub_path, encrypted=False)

    book = parse_epub(epub_path)
    assert not book.drm_protected
    assert book.title == "Test Book"
    assert book.author == "Test Author"
    assert book.cover_bytes == b"FAKECONTENTCOVER"
    assert book.cover_filename == "cover.jpg"
    assert len(book.chapters) == 1
    assert "The night was cold and damp." in book.chapters[0].content


def test_parse_encrypted_epub(tmp_path: Path):
    epub_path = tmp_path / "locked.epub"
    create_dummy_epub(epub_path, encrypted=True)

    book = parse_epub(epub_path)
    assert book.drm_protected


def test_parse_epub3_cover_and_multiple_chapters(tmp_path: Path):
    epub_path = tmp_path / "epub3.epub"
    create_dummy_epub(epub_path, encrypted=False, epub3_cover=True)

    book = parse_epub(epub_path)
    assert not book.drm_protected
    assert book.title == "EPUB3 Test Book"
    assert book.author == "EPUB3 Author"
    assert book.cover_bytes == b"PNGCOVERBYTES"
    assert book.cover_filename == "cover_art.png"
    assert len(book.chapters) == 2
    assert "First chapter content." in book.chapters[0].content
    assert "Second chapter content." in book.chapters[1].content


def test_parse_corrupt_epub(tmp_path: Path):
    corrupt_path = tmp_path / "corrupt.epub"
    with zipfile.ZipFile(corrupt_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        # missing container.xml
    book = parse_epub(corrupt_path)
    assert book.title == "Corrupt EPUB"


def test_path_normalization_and_url_decoding(tmp_path: Path):
    epub_path = tmp_path / "normalized.epub"
    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )
        opf_content = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Normalized Paths Book</dc:title>
  </metadata>
  <manifest>
    <item id="cov" href="../images/My%20Cover.jpg" media-type="image/jpeg" properties="cover-image"/>
    <item id="c1" href="../text/Chapter%201.xhtml#intro" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="c1"/>
  </spine>
</package>"""
        zf.writestr("OEBPS/content/content.opf", opf_content)
        zf.writestr("OEBPS/images/My Cover.jpg", b"NORMCOVERBYTES")
        zf.writestr("OEBPS/text/Chapter 1.xhtml", "<html><body><p>Normalized Content</p></body></html>")

    book = parse_epub(epub_path)
    assert book.cover_bytes == b"NORMCOVERBYTES"
    assert book.cover_filename == "My Cover.jpg"
    assert len(book.chapters) == 1
    assert "Normalized Content" in book.chapters[0].content


def test_epub_lifecycle_and_context_manager(tmp_path: Path):
    epub_path = tmp_path / "lifecycle.epub"
    create_dummy_epub(epub_path, encrypted=False)

    with parse_epub(epub_path) as book:
        assert book.raw_archive is not None
        assert not book.raw_archive.fp is None

    assert book.raw_archive is None

    # Idempotent close
    book.close()
    assert book.raw_archive is None


def test_cover_fallback_when_cover_id_missing_in_archive(tmp_path: Path):
    epub_path = tmp_path / "fallback.epub"
    with zipfile.ZipFile(epub_path, "w") as zf:
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
        opf_content = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Fallback Book</dc:title>
    <meta name="cover" content="missing-cover-id"/>
  </metadata>
  <manifest>
    <item id="missing-cover-id" href="images/missing.jpg" media-type="image/jpeg"/>
    <item id="real-cover" href="images/cover_fallback.png" media-type="image/png"/>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
  </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", opf_content)
        # Note: missing.jpg is NOT written to archive
        zf.writestr("OEBPS/images/cover_fallback.png", b"FALLBACKCOVER")
        zf.writestr("OEBPS/ch1.xhtml", "<html><body><p>Chapter</p></body></html>")

    book = parse_epub(epub_path)
    assert book.cover_bytes == b"FALLBACKCOVER"
    assert book.cover_filename == "cover_fallback.png"


def test_parse_epub_with_str_path(tmp_path: Path):
    epub_path = tmp_path / "str_path.epub"
    create_dummy_epub(epub_path, encrypted=False)

    book = parse_epub(str(epub_path))
    assert isinstance(book.file_path, Path)
    assert book.title == "Test Book"
    assert book.cover_bytes == b"FAKECONTENTCOVER"
    book.close()
