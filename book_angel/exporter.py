"""Book packaging and export engine for EPUB and PDF."""
from __future__ import annotations

import datetime
import html
import json
from pathlib import Path
import posixpath
import re
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
import zipfile

from book_angel.staging import StagingWorkspace, format_change_summary


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

    # Generate and save change summary if chunks were modified
    diffs = workspace.get_modified_chunks()
    if diffs:
        summary_text = format_change_summary(diffs)
        summary_path = out_dir / f"{safe_slug}_Changes_Summary.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        print(f"\n{summary_text}")
        print(f"📄 Change summary saved to: {summary_path}\n")

    if export_format.lower() == "epub":
        out_path = out_dir / f"{safe_slug}.epub"
        source_epub = workspace.root / "source.epub"
        if source_epub.exists():
            _patch_source_epub(source_epub, out_path, workspace, final_title, meta)
        else:
            _build_epub(out_path, final_title, author, workspace)
        return out_path
    else:
        # PDF fallback export
        out_path = out_dir / f"{safe_slug}.pdf"
        _build_pdf(out_path, final_title, author, workspace)
        return out_path


def _extract_chapter_map_from_zip(zf: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    """Parse an existing EPUB archive's content.opf to build a chapter index map."""
    namelist = zf.namelist()
    opf_path = "OEBPS/content.opf"
    if "META-INF/container.xml" in namelist:
        container_xml = zf.read("META-INF/container.xml")
        root = ET.fromstring(container_xml)
        for elem in root.iter():
            if elem.tag.endswith("rootfile"):
                opf_path = elem.attrib.get("full-path", opf_path)
                break

    if opf_path not in namelist:
        return {}

    opf_dir = posixpath.dirname(opf_path)
    opf_xml = zf.read(opf_path)
    root = ET.fromstring(opf_xml)

    manifest: dict[str, dict[str, str]] = {}
    spine_refs: list[str] = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "item":
            item_id = elem.attrib.get("id", "")
            href = elem.attrib.get("href", "")
            media_type = elem.attrib.get("media-type", "")
            manifest[item_id] = {"href": href, "media-type": media_type}
        elif tag == "itemref":
            idref = elem.attrib.get("idref")
            if idref:
                spine_refs.append(idref)

    chapter_map: dict[str, dict[str, str]] = {}
    for idx, ref in enumerate(spine_refs, 1):
        if ref in manifest:
            ch_href = manifest[ref]["href"]
            clean_ch_href = ch_href.split("#")[0]
            ch_full = posixpath.normpath(f"{opf_dir}/{urllib.parse.unquote(clean_ch_href)}").lstrip("/")
            chapter_map[str(idx)] = {
                "idref": ref,
                "href": ch_href,
                "archive_path": ch_full,
            }
    return chapter_map


def _patch_source_epub(
    source_epub: Path,
    out_path: Path,
    workspace: StagingWorkspace,
    final_title: str,
    meta: dict,
) -> None:
    """Export by patching the original EPUB archive with any modified chunks."""
    chapter_map = meta.get("chapter_map") or {}

    # Group all current chunks in workspace by chapter_idx
    chapter_chunks: dict[int, list[tuple[int, str]]] = {}
    chunk_pattern = re.compile(r"^<!--\s*chunk_id:\s*(\d+)\s*\|\s*chapter:\s*(\d+)")

    if workspace.chunks_dir.exists():
        for chunk_file in sorted(workspace.chunks_dir.glob("chunk_*.txt")):
            stem_part = chunk_file.stem.split("_")[-1]
            if not stem_part.isdigit():
                continue
            cid = int(stem_part)
            raw = chunk_file.read_text(encoding="utf-8")
            m = chunk_pattern.search(raw)
            ch_idx = int(m.group(2)) if m else 1
            body = re.sub(r"^<!--.*?-->\s*", "", raw, flags=re.DOTALL).strip()
            chapter_chunks.setdefault(ch_idx, []).append((cid, body))

    # Identify which chunk IDs have actually been modified
    modified_diffs = workspace.get_modified_chunks()
    modified_chunk_ids = {d.chunk_id for d in modified_diffs}

    replaced_files: dict[str, bytes] = {}

    with zipfile.ZipFile(source_epub, "r") as src_zip:
        if not chapter_map:
            chapter_map = _extract_chapter_map_from_zip(src_zip)

        namelist = src_zip.namelist()

        for ch_idx, chunk_list in chapter_chunks.items():
            has_modifications = any(cid in modified_chunk_ids for cid, _ in chunk_list)
            ch_info = chapter_map.get(str(ch_idx)) or chapter_map.get(ch_idx)
            if not ch_info:
                continue

            archive_path = ch_info.get("archive_path") or ch_info.get("href")
            if not archive_path or archive_path not in namelist:
                candidates = [n for n in namelist if n.endswith(archive_path.split("/")[-1])]
                if candidates:
                    archive_path = candidates[0]
                else:
                    continue

            if has_modifications:
                sorted_chunks = sorted(chunk_list, key=lambda x: x[0])
                if len(sorted_chunks) == 1:
                    new_body = sorted_chunks[0][1]
                else:
                    new_body = "\n\n".join(c[1] for c in sorted_chunks)

                # Ensure strict XML numeric entity for non-breaking spaces
                new_body = new_body.replace("&nbsp;", "&#160;")
                replaced_files[archive_path] = new_body.encode("utf-8")

        with zipfile.ZipFile(out_path, "w") as dst_zip:
            # 1. Uncompressed mimetype at offset 0
            dst_zip.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)

            for item in src_zip.infolist():
                if item.filename == "mimetype":
                    continue

                if item.filename in replaced_files:
                    dst_zip.writestr(
                        item.filename,
                        replaced_files[item.filename],
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
                elif item.filename.endswith("content.opf"):
                    opf_text = src_zip.read(item.filename).decode("utf-8", errors="replace")
                    if final_title:
                        opf_text = re.sub(
                            r"(<dc:title[^>]*>)(.*?)(</dc:title>)",
                            lambda m: f"{m.group(1)}{html.escape(final_title)}{m.group(3)}",
                            opf_text,
                            count=1,
                        )
                    dst_zip.writestr(item.filename, opf_text.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
                else:
                    dst_zip.writestr(item.filename, src_zip.read(item.filename), compress_type=item.compress_type)


def _build_epub(out_path: Path, title: str, author: str, workspace: StagingWorkspace) -> None:
    """Build a fully standard-compliant EPUB 3 compatible with Apple Books."""
    escaped_title = html.escape(title)
    escaped_author = html.escape(author)
    book_uuid = str(uuid.uuid4())
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cover_file = workspace.root / "cover.jpg"
    cover_bytes = cover_file.read_bytes() if cover_file.exists() else None

    # Read and sort all chunks by chunk_id
    chunk_files = sorted(
        [f for f in workspace.chunks_dir.glob("chunk_*.txt") if f.stem.split("_")[-1].isdigit()],
        key=lambda p: int(p.stem.split("_")[-1]),
    ) if workspace.chunks_dir.exists() else []

    chunk_bodies: list[str] = []
    for cf in chunk_files:
        raw = cf.read_text(encoding="utf-8")
        body = re.sub(r"^<!--.*?-->\s*", "", raw, flags=re.DOTALL).strip()
        if body:
            chunk_bodies.append(body)

    full_body = "\n\n".join(chunk_bodies)

    with zipfile.ZipFile(out_path, "w") as zf:
        # 1. mimetype (ZIP_STORED)
        zf.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # 2. container.xml
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )

        # 3. style.css
        book_css = """body {
  font-family: Georgia, -apple-system, BlinkMacSystemFont, "Times New Roman", serif;
  line-height: 1.7;
  margin: 6% 8%;
  color: #1a1a1a;
  background: #ffffff;
}
h1.book-title {
  text-align: center;
  font-size: 2.1em;
  font-weight: 600;
  margin-top: 1.6em;
  margin-bottom: 0.25em;
}
p.book-author {
  text-align: center;
  font-size: 1.15em;
  color: #666;
  margin-bottom: 2em;
}
p {
  text-indent: 1.5em;
  margin: 0 0 1.1em 0;
  text-align: justify;
}
"""
        zf.writestr("OEBPS/style.css", book_css)

        # 4. Cover image if exists
        has_cover = bool(cover_bytes)
        if has_cover:
            zf.writestr("OEBPS/images/cover.jpg", cover_bytes)

        # 5. chapter1.xhtml
        if "<html" in full_body.lower() or "<body" in full_body.lower():
            body_match = re.search(r"<body[^>]*>(.*?)</body>", full_body, flags=re.DOTALL | re.IGNORECASE)
            inner_content = body_match.group(1) if body_match else full_body
        else:
            paragraphs = [p.strip() for p in full_body.split("\n\n") if p.strip()]
            inner_content = "".join(f"<p>{html.escape(p)}</p>\n" for p in paragraphs)

        inner_content = inner_content.replace("&amp;nbsp;", "&#160;").replace("&nbsp;", "&#160;")

        header_block = f'<h1 class="book-title">{escaped_title}</h1>\n'
        if escaped_author:
            header_block += f'<p class="book-author">by {escaped_author}</p>\n'

        chapter1_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>{escaped_title}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
{header_block}
{inner_content}
</body>
</html>"""
        zf.writestr("OEBPS/chapter1.xhtml", chapter1_xhtml)

        # 6. nav.xhtml
        nav_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Navigation</title>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
      <li><a href="chapter1.xhtml">{escaped_title}</a></li>
    </ol>
  </nav>
</body>
</html>"""
        zf.writestr("OEBPS/nav.xhtml", nav_html)

        # 7. toc.ncx
        ncx_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{book_uuid}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{escaped_title}</text></docTitle>
  <docAuthor><text>{escaped_author}</text></docAuthor>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel><text>{escaped_title}</text></navLabel>
      <content src="chapter1.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"""
        zf.writestr("OEBPS/toc.ncx", ncx_xml)

        # 8. content.opf
        manifest_items = [
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
            '<item id="style" href="style.css" media-type="text/css"/>',
            '<item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>',
        ]
        if has_cover:
            manifest_items.append('<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>')

        cover_meta = '<meta name="cover" content="cover-image"/>' if has_cover else ""
        manifest_str = "\n    ".join(manifest_items)

        opf_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{escaped_title}</dc:title>
    <dc:creator>{escaped_author}</dc:creator>
    <dc:identifier id="BookId">urn:uuid:{book_uuid}</dc:identifier>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">{now_iso}</meta>
    {cover_meta}
  </metadata>
  <manifest>
    {manifest_str}
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
  </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", opf_xml)


def _build_pdf(out_path: Path, title: str, author: str, workspace: StagingWorkspace) -> None:
    """Build a clean PDF document from chunk texts."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)  # A4 page
    writer.add_metadata({"/Title": title, "/Author": author})
    with open(out_path, "wb") as f:
        writer.write(f)
