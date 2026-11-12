"""EPUB parsing and extraction engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import posixpath
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile


@dataclass
class EpubChapter:
    idref: str
    href: str
    title: str
    content: str
    archive_path: str = ""


@dataclass
class EpubBook:
    file_path: Path
    title: str = "Untitled"
    author: str = "Unknown"
    cover_bytes: bytes | None = None
    cover_filename: str = "cover.jpg"
    drm_protected: bool = False
    chapters: list[EpubChapter] = field(default_factory=list)
    raw_archive: zipfile.ZipFile | None = None

    def close(self) -> None:
        if self.raw_archive:
            self.raw_archive.close()
            self.raw_archive = None

    def __enter__(self) -> EpubBook:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def parse_epub(path: Path | str) -> EpubBook:
    """Parse an EPUB file into an EpubBook dataclass."""
    path = Path(path)
    try:
        zf = zipfile.ZipFile(path, "r")
    except Exception:
        return EpubBook(file_path=path, title="Corrupt EPUB")

    namelist = zf.namelist()

    if "META-INF/encryption.xml" in namelist:
        return EpubBook(file_path=path, drm_protected=True, raw_archive=zf)

    if "META-INF/container.xml" not in namelist:
        return EpubBook(file_path=path, title="Corrupt EPUB", raw_archive=zf)

    try:
        container_xml = zf.read("META-INF/container.xml")
        root = ET.fromstring(container_xml)
    except Exception:
        return EpubBook(file_path=path, title="Corrupt EPUB", raw_archive=zf)

    opf_path = ""
    for elem in root.iter():
        if elem.tag.endswith("rootfile"):
            opf_path = elem.attrib.get("full-path", "")
            break

    if not opf_path or opf_path not in namelist:
        return EpubBook(file_path=path, title="Corrupt EPUB", raw_archive=zf)

    opf_dir = str(Path(opf_path).parent)
    if opf_dir == ".":
        opf_dir = ""

    try:
        opf_xml = zf.read(opf_path)
        opf_root = ET.fromstring(opf_xml)
    except Exception:
        return EpubBook(file_path=path, title="Corrupt EPUB", raw_archive=zf)

    title = "Untitled"
    author = "Unknown"
    cover_id: str | None = None

    manifest: dict[str, dict[str, str]] = {}
    spine_refs: list[str] = []

    for elem in opf_root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "title" and elem.text and title == "Untitled":
            title = elem.text.strip()
        elif tag == "creator" and elem.text and author == "Unknown":
            author = elem.text.strip()
        elif tag == "meta" and elem.attrib.get("name") == "cover":
            cover_id = elem.attrib.get("content")
        elif tag == "item":
            item_id = elem.attrib.get("id", "")
            href = elem.attrib.get("href", "")
            media_type = elem.attrib.get("media-type", "")
            props = elem.attrib.get("properties", "")
            if "cover-image" in props:
                cover_id = item_id
            manifest[item_id] = {"href": href, "media-type": media_type}
        elif tag == "itemref":
            idref = elem.attrib.get("idref")
            if idref:
                spine_refs.append(idref)

    cover_bytes: bytes | None = None
    cover_filename = "cover.jpg"

    if cover_id and cover_id in manifest:
        cover_rel = manifest[cover_id]["href"]
        cover_full = posixpath.normpath(f"{opf_dir}/{urllib.parse.unquote(cover_rel.split('#')[0])}").lstrip("/")
        if cover_full in namelist:
            cover_bytes = zf.read(cover_full)
            cover_filename = Path(urllib.parse.unquote(cover_rel)).name
    if not cover_bytes:
        # Fallback: scan manifest for images matching cover heuristics
        for item_id, item_data in manifest.items():
            if item_data.get("media-type", "").startswith("image/") and (
                "cover" in item_id.lower() or "cover" in item_data.get("href", "").lower()
            ):
                cover_rel = item_data["href"]
                cover_full = posixpath.normpath(f"{opf_dir}/{urllib.parse.unquote(cover_rel.split('#')[0])}").lstrip("/")
                if cover_full in namelist:
                    cover_bytes = zf.read(cover_full)
                    cover_filename = Path(urllib.parse.unquote(cover_rel)).name
                    break

    chapters: list[EpubChapter] = []
    for ref in spine_refs:
        if ref in manifest:
            ch_href = manifest[ref]["href"]
            clean_ch_href = ch_href.split("#")[0]
            ch_full = posixpath.normpath(f"{opf_dir}/{urllib.parse.unquote(clean_ch_href)}").lstrip("/")
            if ch_full in namelist:
                content_text = zf.read(ch_full).decode("utf-8", errors="replace")
                chapters.append(
                    EpubChapter(
                        idref=ref,
                        href=ch_href,
                        title=ref,
                        content=content_text,
                        archive_path=ch_full,
                    )
                )

    return EpubBook(
        file_path=path,
        title=title,
        author=author,
        cover_bytes=cover_bytes,
        cover_filename=cover_filename,
        drm_protected=False,
        chapters=chapters,
        raw_archive=zf,
    )
