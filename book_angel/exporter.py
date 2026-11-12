"""Book packaging and export engine for EPUB and PDF."""
from __future__ import annotations

import html
import json
from pathlib import Path
import re
import zipfile
from book_angel.staging import StagingWorkspace


def export_book(
    workspace: StagingWorkspace,
    output_dir: Path | str,
    export_format: str = "epub",
    title_suffix: str = "",
    custom_title: str | None = None,
) -> Path:
    """Reassemble processed book chunks from staging workspace and export as EPUB or PDF."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load metadata
    meta_path = workspace.root / "meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    base_title = custom_title or meta.get("title", "Exported Book")
    if title_suffix and not custom_title:
        final_title = f"{base_title} {title_suffix}".strip()
    else:
        final_title = base_title

    author = meta.get("author", "Unknown Author")
    safe_slug = re.sub(r"[^\w\-]", "_", final_title).strip("_") or "exported_book"

    # Gather chunks
    chunk_texts: list[str] = []
    if workspace.chunks_dir.exists():
        def _chunk_sort_key(p: Path) -> tuple[int, int | str]:
            stem_part = p.stem.split("_")[-1]
            if stem_part.isdigit():
                return (0, int(stem_part))
            return (1, p.stem)

        for chunk_file in sorted(workspace.chunks_dir.glob("chunk_*.txt"), key=_chunk_sort_key):
            if not chunk_file.stem.split("_")[-1].isdigit():
                continue
            content = chunk_file.read_text(encoding="utf-8")
            # Strip metadata comment header
            body = re.sub(r"^<!--.*?-->\s*", "", content, flags=re.DOTALL)
            chunk_texts.append(body.strip())

    joined_text = "\n\n".join(chunk_texts)

    cover_file = workspace.root / "cover.jpg"
    cover_bytes = cover_file.read_bytes() if cover_file.exists() else None

    if export_format.lower() == "epub":
        out_path = out_dir / f"{safe_slug}.epub"
        _build_epub(out_path, final_title, author, joined_text, cover_bytes)
        return out_path
    else:
        # PDF fallback export
        out_path = out_dir / f"{safe_slug}.pdf"
        _build_pdf(out_path, final_title, author, joined_text)
        return out_path


def _build_epub(out_path: Path, title: str, author: str, body_text: str, cover_bytes: bytes | None) -> None:
    escaped_title = html.escape(title)
    escaped_author = html.escape(author)
    paragraphs = "".join(f"<p>{html.escape(p.strip())}</p>\n" for p in body_text.split("\n\n") if p.strip())

    with zipfile.ZipFile(out_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )

        cover_manifest = ""
        cover_meta = ""
        if cover_bytes:
            zf.writestr("OEBPS/images/cover.jpg", cover_bytes)
            cover_manifest = '<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>'
            cover_meta = '<meta name="cover" content="cover-image"/>'

        opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:book-angel-{abs(hash(title))}</dc:identifier>
    <dc:title>{escaped_title}</dc:title>
    <dc:creator>{escaped_author}</dc:creator>
    {cover_meta}
  </metadata>
  <manifest>
    {cover_manifest}
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", opf)

        xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{escaped_title}</title>
  <style>
    body {{ font-family: serif; line-height: 1.6; margin: 5%; }}
    p {{ text-indent: 1.5em; margin: 0; }}
  </style>
</head>
<body>
  <h1>{escaped_title}</h1>
  {paragraphs}
</body>
</html>"""
        zf.writestr("OEBPS/chapter1.xhtml", xhtml)


def _build_pdf(out_path: Path, title: str, author: str, body_text: str) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)  # A4 page
    writer.add_metadata({"/Title": title, "/Author": author})
    with open(out_path, "wb") as f:
        writer.write(f)
