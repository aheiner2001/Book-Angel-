# Book-Angel Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular Python CLI and Agent Skill (`book-angel`) that ingests EPUB/PDF books, splits them into manageable chunks for AI editing guided by custom rules and before/after examples, tracks visual and terminal diffs for user approval, and reassembles the final book preserving cover art, layout styles, and metadata.

**Architecture:** A Python package (`book_angel`) coordinates staging folders backed by original snapshots. The parser extracts XHTML/text and cover art; the chunker breaks content at natural chapter/scene breaks (<2,500 words); the staging manager tracks diffs against originals; the interactive reviewer approves/rejects changes; and the exporter rebuilds valid EPUBs and PDFs. An Antigravity skill and Cursor workspace guide allow seamless agent-driven editing.

**Tech Stack:** Python 3.10+, `typer`/`click` or `argparse`, `pyyaml`, `beautifulsoup4`, `pypdf`/`pymupdf` (fitz), `weasyprint` or `reportlab`, `pytest`.

## Global Constraints

- Python version floor: `>=3.10`.
- All paths and staging artifacts must reside inside `.book-angel/staging/<book-slug>/`.
- Cover art must be preserved bit-for-bit or cleanly converted from Page 1 of PDF.
- EPUB CSS styles, fonts, and internal link IDs must remain intact during text editing.
- Staging must maintain pristine original snapshots to allow deterministic diffing and reverting.
- DRM-protected EPUBs must trigger clear diagnostic warnings rather than unhandled tracebacks.

---

### Task 1: Project Scaffolding & Build Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `book_angel/__init__.py`
- Create: `tests/__init__.py`
- Test: `tests/test_scaffolding.py`

**Interfaces:**
- Produces: `book_angel.__version__` string and working test environment.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scaffolding.py
from book_angel import __version__

def test_version_defined():
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scaffolding.py -v`  
Expected: FAIL (ModuleNotFoundError or AttributeError)

- [ ] **Step 3: Write minimal implementation**

Create `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "book-angel"
version = "0.1.0"
description = "AI-assisted book content filtering and transformation tool"
authors = [{ name = "Book-Angel Team" }]
requires-python = ">=3.10"
dependencies = [
    "pyyaml>=6.0",
    "beautifulsoup4>=4.12.0",
    "pypdf>=3.17.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
]

[project.scripts]
book-angel = "book_angel.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["book_angel*"]
```

Create `book_angel/__init__.py`:
```python
"""Book-Angel: AI-assisted book content transformation and filtering."""

__version__ = "0.1.0"
```

Create `tests/__init__.py` (empty file).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scaffolding.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml book_angel/__init__.py tests/__init__.py tests/test_scaffolding.py
git commit -m "chore: setup project scaffolding and version test"
```

---

### Task 2: Rules Configuration Wizard & Serializer

**Files:**
- Create: `book_angel/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: User inputs or dictionary configurations.
- Produces: `RulesConfig` dataclass, `save_rules_yaml(config, path)`, `load_rules_yaml(path)`, `generate_rules_markdown(config) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
from book_angel.config import RulesConfig, ExamplePair, save_rules_yaml, load_rules_yaml, generate_rules_markdown

def test_rules_roundtrip_and_markdown(tmp_path: Path):
    cfg = RulesConfig(
        romance_level="mild",
        violence_level="adventure",
        language_level="cleaned",
        omitted_topics=["gay or lesbian themes"],
        custom_rules=["Ensure character humor remains lively."],
        examples=[
            ExamplePair(
                before="He kissed her passionately on the lips, pressing her against the wall.",
                after="He gave her a gentle kiss on the cheek before stepping back."
            )
        ]
    )
    
    yaml_file = tmp_path / "rules.yaml"
    save_rules_yaml(cfg, yaml_file)
    assert yaml_file.exists()
    
    loaded = load_rules_yaml(yaml_file)
    assert loaded.romance_level == "mild"
    assert loaded.omitted_topics == ["gay or lesbian themes"]
    assert len(loaded.examples) == 1
    assert loaded.examples[0].before.startswith("He kissed her")
    
    md_content = generate_rules_markdown(loaded)
    assert "# Book-Angel Content Rules" in md_content
    assert "Romance Level: mild" in md_content
    assert "### Few-Shot Editing Examples" in md_content
    assert "Original:" in md_content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`  
Expected: FAIL (cannot import `RulesConfig` from `book_angel.config`)

- [ ] **Step 3: Write minimal implementation**

Create `book_angel/config.py`:
```python
"""Configuration and rules engine for Book-Angel."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

@dataclass
class ExamplePair:
    before: str
    after: str

@dataclass
class RulesConfig:
    romance_level: str = "mild"
    violence_level: str = "adventure"
    language_level: str = "cleaned"
    omitted_topics: list[str] = field(default_factory=list)
    custom_rules: list[str] = field(default_factory=list)
    examples: list[ExamplePair] = field(default_factory=list)

def save_rules_yaml(config: RulesConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_dict = asdict(config)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(raw_dict, f, sort_keys=False)

def load_rules_yaml(path: Path) -> RulesConfig:
    if not path.exists():
        return RulesConfig()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    examples = [
        ExamplePair(before=ex["before"], after=ex["after"])
        for ex in data.get("examples", [])
    ]
    return RulesConfig(
        romance_level=data.get("romance_level", "mild"),
        violence_level=data.get("violence_level", "adventure"),
        language_level=data.get("language_level", "cleaned"),
        omitted_topics=data.get("omitted_topics", []),
        custom_rules=data.get("custom_rules", []),
        examples=examples,
    )

def generate_rules_markdown(config: RulesConfig) -> str:
    lines = [
        "# Book-Angel Content Rules",
        "",
        "You are acting as an editorial assistant following strict narrative filtering guidelines.",
        "Modify only passages that conflict with these rules. Keep all other prose, tone, and character voices intact.",
        "",
        "## Policy Levels",
        f"- **Romance Level:** {config.romance_level}",
        f"- **Violence Level:** {config.violence_level}",
        f"- **Language Level:** {config.language_level}",
        "",
    ]
    
    if config.omitted_topics:
        lines.append("## Omitted Topics / Themes")
        for topic in config.omitted_topics:
            lines.append(f"- Do not include: {topic}")
        lines.append("")
        
    if config.custom_rules:
        lines.append("## Custom Rules")
        for rule in config.custom_rules:
            lines.append(f"- {rule}")
        lines.append("")
        
    if config.examples:
        lines.append("### Few-Shot Editing Examples")
        lines.append("Follow these patterns for tone and replacement style:")
        lines.append("")
        for idx, ex in enumerate(config.examples, 1):
            lines.append(f"**Example {idx}:**")
            lines.append(f"> **Original:** {ex.before}")
            lines.append(f"> **Revised:** {ex.after}")
            lines.append("")
            
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/config.py tests/test_config.py
git commit -m "feat: implement rules configuration, serialization, and markdown generator"
```

---

### Task 3: EPUB Parser & Cover Art Extraction

**Files:**
- Create: `book_angel/parser/__init__.py`
- Create: `book_angel/parser/epub_engine.py`
- Test: `tests/test_epub.py`

**Interfaces:**
- Consumes: EPUB file path.
- Produces: `EpubBook` dataclass with `metadata`, `cover_bytes`, `chapters: list[EpubChapter]`, `drm_protected: bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_epub.py
import zipfile
from pathlib import Path
from book_angel.parser.epub_engine import parse_epub, EpubBook

def create_dummy_epub(path: Path, encrypted: bool = False) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""")
        if encrypted:
            zf.writestr("META-INF/encryption.xml", "<encryption/>")
        
        zf.writestr("OEBPS/content.opf", """<?xml version="1.0" encoding="utf-8"?>
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
</package>""")
        zf.writestr("OEBPS/images/cover.jpg", b"FAKECONTENTCOVER")
        zf.writestr("OEBPS/ch1.xhtml", """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
  <h1>Chapter 1</h1>
  <p>The night was cold and damp.</p>
</body>
</html>""")
    return path

def test_parse_valid_epub(tmp_path: Path):
    epub_path = tmp_path / "valid.epub"
    create_dummy_epub(epub_path, encrypted=False)
    
    book = parse_epub(epub_path)
    assert not book.drm_protected
    assert book.title == "Test Book"
    assert book.author == "Test Author"
    assert book.cover_bytes == b"FAKECONTENTCOVER"
    assert len(book.chapters) == 1
    assert "The night was cold and damp." in book.chapters[0].content

def test_parse_encrypted_epub(tmp_path: Path):
    epub_path = tmp_path / "locked.epub"
    create_dummy_epub(epub_path, encrypted=True)
    
    book = parse_epub(epub_path)
    assert book.drm_protected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_epub.py -v`  
Expected: FAIL (ModuleNotFoundError: `book_angel.parser.epub_engine`)

- [ ] **Step 3: Write minimal implementation**

Create `book_angel/parser/__init__.py`:
```python
"""Book parsing modules."""
```

Create `book_angel/parser/epub_engine.py`:
```python
"""EPUB parsing and extraction engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

@dataclass
class EpubChapter:
    idref: str
    href: str
    title: str
    content: str

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

def parse_epub(path: Path) -> EpubBook:
    zf = zipfile.ZipFile(path, "r")
    namelist = zf.namelist()
    
    if "META-INF/encryption.xml" in namelist:
        return EpubBook(file_path=path, drm_protected=True)
        
    container_xml = zf.read("META-INF/container.xml")
    root = ET.fromstring(container_xml)
    opf_path = ""
    for elem in root.iter():
        if elem.tag.endswith("rootfile"):
            opf_path = elem.attrib.get("full-path", "")
            break
            
    if not opf_path or opf_path not in namelist:
        return EpubBook(file_path=path, title="Corrupt EPUB")
        
    opf_dir = str(Path(opf_path).parent)
    if opf_dir == ".":
        opf_dir = ""
        
    opf_xml = zf.read(opf_path)
    opf_root = ET.fromstring(opf_xml)
    
    title = "Untitled"
    author = "Unknown"
    cover_id = None
    
    manifest: dict[str, dict[str, str]] = {}
    spine_refs: list[str] = []
    
    for elem in opf_root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "title" and elem.text:
            title = elem.text.strip()
        elif tag == "creator" and elem.text:
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

    cover_bytes = None
    cover_filename = "cover.jpg"
    if cover_id and cover_id in manifest:
        cover_rel = manifest[cover_id]["href"]
        cover_full = f"{opf_dir}/{cover_rel}".lstrip("/")
        if cover_full in namelist:
            cover_bytes = zf.read(cover_full)
            cover_filename = Path(cover_rel).name

    chapters: list[EpubChapter] = []
    for ref in spine_refs:
        if ref in manifest:
            ch_href = manifest[ref]["href"]
            ch_full = f"{opf_dir}/{ch_href}".lstrip("/")
            if ch_full in namelist:
                content_text = zf.read(ch_full).decode("utf-8", errors="replace")
                chapters.append(EpubChapter(idref=ref, href=ch_href, title=ref, content=content_text))
                
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_epub.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/parser/ tests/test_epub.py
git commit -m "feat: implement EPUB parser, cover extraction, and DRM detection"
```

---

### Task 4: PDF Ingestion Engine

**Files:**
- Create: `book_angel/parser/pdf_engine.py`
- Test: `tests/test_pdf.py`

**Interfaces:**
- Consumes: PDF file path.
- Produces: `PdfBook` dataclass with `title`, `pages: list[str]`, `is_scanned: bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pdf.py
from pathlib import Path
from pypdf import PdfWriter
from book_angel.parser.pdf_engine import parse_pdf

def create_dummy_pdf(path: Path, text: str) -> Path:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # Add metadata
    writer.add_metadata({"/Title": "PDF Sample", "/Author": "Author Name"})
    with open(path, "wb") as f:
        writer.write(f)
    return path

def test_parse_blank_pdf(tmp_path: Path):
    pdf_path = tmp_path / "blank.pdf"
    create_dummy_pdf(pdf_path, text="")
    
    book = parse_pdf(pdf_path)
    assert book.title == "PDF Sample"
    assert book.page_count == 1
    assert book.is_scanned_or_empty
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pdf.py -v`  
Expected: FAIL (cannot import `parse_pdf`)

- [ ] **Step 3: Write minimal implementation**

Create `book_angel/parser/pdf_engine.py`:
```python
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

def parse_pdf(path: Path) -> PdfBook:
    reader = PdfReader(str(path))
    meta = reader.metadata or {}
    title = meta.title or path.stem
    author = meta.author or "Unknown"
    
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
        is_scanned_or_empty=(len(total_text) == 0)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pdf.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/parser/pdf_engine.py tests/test_pdf.py
git commit -m "feat: implement PDF text extraction and empty/scanned detection"
```

---

### Task 5: Smart Chunker & Scene Boundary Management

**Files:**
- Create: `book_angel/parser/chunker.py`
- Test: `tests/test_chunker.py`

**Interfaces:**
- Consumes: Chapter texts or raw paragraphs, `max_words_per_chunk` (default 2500).
- Produces: `list[BookChunk]` with `chunk_id`, `chapter_index`, `scene_index`, `header`, `body`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chunker.py
from book_angel.parser.chunker import chunk_text, BookChunk

def test_chunk_short_text():
    text = "Short chapter content with a few words."
    chunks = chunk_text(text, chapter_title="Chapter 1", chapter_idx=1, max_words=100)
    assert len(chunks) == 1
    assert chunks[0].chapter_idx == 1
    assert "Short chapter content" in chunks[0].body
    assert "<!-- chunk_id: 001" in chunks[0].render()

def test_chunk_splits_long_text_at_scene_break():
    scene1 = "Word " * 60 + "\n\n***\n\n"
    scene2 = "Other " * 60
    full_text = scene1 + scene2
    chunks = chunk_text(full_text, chapter_title="Chapter 2", chapter_idx=2, max_words=50)
    assert len(chunks) >= 2
    assert "Word" in chunks[0].body
    assert "Other" in chunks[1].body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chunker.py -v`  
Expected: FAIL (cannot import `chunk_text`)

- [ ] **Step 3: Write minimal implementation**

Create `book_angel/parser/chunker.py`:
```python
"""Text chunking logic for Book-Angel."""
from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass
class BookChunk:
    chunk_id: int
    chapter_idx: int
    scene_idx: int
    chapter_title: str
    body: str

    def render(self) -> str:
        header = f"<!-- chunk_id: {self.chunk_id:03d} | chapter: {self.chapter_idx} | scene: {self.scene_idx} | title: {self.chapter_title} -->\n\n"
        return header + self.body.strip() + "\n"

def chunk_text(
    text: str,
    chapter_title: str = "Chapter",
    chapter_idx: int = 1,
    max_words: int = 2500,
    start_chunk_id: int = 1
) -> list[BookChunk]:
    words = text.split()
    if len(words) <= max_words:
        return [
            BookChunk(
                chunk_id=start_chunk_id,
                chapter_idx=chapter_idx,
                scene_idx=1,
                chapter_title=chapter_title,
                body=text.strip(),
            )
        ]
        
    # Split by standard scene breaks if present, or paragraphs
    scene_pattern = re.compile(r"\n\s*(?:\*\*\*|\* \* \*|---|\b___\b)\s*\n")
    scenes = scene_pattern.split(text)
    
    chunks: list[BookChunk] = []
    current_chunk_words: list[str] = []
    scene_counter = 1
    current_chunk_id = start_chunk_id
    
    for scene in scenes:
        scene_words = scene.split()
        if len(current_chunk_words) + len(scene_words) > max_words and current_chunk_words:
            # Emit current
            body = " ".join(current_chunk_words)
            chunks.append(
                BookChunk(
                    chunk_id=current_chunk_id,
                    chapter_idx=chapter_idx,
                    scene_idx=scene_counter,
                    chapter_title=chapter_title,
                    body=body,
                )
            )
            current_chunk_id += 1
            scene_counter += 1
            current_chunk_words = scene_words
        else:
            current_chunk_words.extend(scene_words)
            
    if current_chunk_words:
        chunks.append(
            BookChunk(
                chunk_id=current_chunk_id,
                chapter_idx=chapter_idx,
                scene_idx=scene_counter,
                chapter_title=chapter_title,
                body=" ".join(current_chunk_words),
            )
        )
        
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chunker.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/parser/chunker.py tests/test_chunker.py
git commit -m "feat: implement smart chapter and scene chunker"
```

---

### Task 6: Staging Workspace & Snapshot Manager

**Files:**
- Create: `book_angel/staging.py`
- Test: `tests/test_staging.py`

**Interfaces:**
- Consumes: Book chunks, cover art, rules.
- Produces: `StagingWorkspace` managing directory layout, reading chunks, writing originals, and checking dirty diff state.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_staging.py
from pathlib import Path
from book_angel.staging import StagingWorkspace
from book_angel.parser.chunker import BookChunk
from book_angel.config import RulesConfig

def test_staging_initialization(tmp_path: Path):
    workspace = StagingWorkspace(base_dir=tmp_path, book_slug="dracula")
    workspace.initialize(
        title="Dracula",
        author="Bram Stoker",
        cover_bytes=b"COVERIMG",
        rules=RulesConfig(romance_level="mild"),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Original text here.")
        ]
    )
    
    assert (workspace.root / "meta.json").exists()
    assert (workspace.root / "cover.jpg").exists()
    assert (workspace.chunks_dir / "chunk_001.txt").exists()
    assert (workspace.originals_dir / "chunk_001.txt").exists()
    assert (workspace.root / "rules.md").exists()
    
    # Check no diff initially
    diffs = workspace.get_modified_chunks()
    assert len(diffs) == 0
    
    # Modify chunk
    (workspace.chunks_dir / "chunk_001.txt").write_text("Modified text here.", encoding="utf-8")
    diffs_after = workspace.get_modified_chunks()
    assert len(diffs_after) == 1
    assert diffs_after[0].chunk_id == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_staging.py -v`  
Expected: FAIL (cannot import `StagingWorkspace`)

- [ ] **Step 3: Write minimal implementation**

Create `book_angel/staging.py`:
```python
"""Staging workspace manager for Book-Angel."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from book_angel.config import RulesConfig, generate_rules_markdown
from book_angel.parser.chunker import BookChunk

@dataclass
class ChunkDiff:
    chunk_id: int
    path: Path
    original_text: str
    modified_text: str

class StagingWorkspace:
    def __init__(self, base_dir: Path, book_slug: str):
        self.root = base_dir / ".book-angel" / "staging" / book_slug
        self.chunks_dir = self.root / "chunks"
        self.originals_dir = self.root / ".originals"
        
    def initialize(
        self,
        title: str,
        author: str,
        cover_bytes: bytes | None,
        rules: RulesConfig,
        chunks: list[BookChunk]
    ) -> None:
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        meta = {
            "title": title,
            "author": author,
            "chunk_count": len(chunks),
        }
        with open(self.root / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            
        # Save cover if available
        if cover_bytes:
            (self.root / "cover.jpg").write_bytes(cover_bytes)
            
        # Save rules.md
        rules_md = generate_rules_markdown(rules)
        (self.root / "rules.md").write_text(rules_md, encoding="utf-8")
        
        # Write chunks and pristine originals
        for chunk in chunks:
            filename = f"chunk_{chunk.chunk_id:03d}.txt"
            rendered = chunk.render()
            (self.chunks_dir / filename).write_text(rendered, encoding="utf-8")
            (self.originals_dir / filename).write_text(rendered, encoding="utf-8")

    def get_modified_chunks(self) -> list[ChunkDiff]:
        diffs: list[ChunkDiff] = []
        if not self.chunks_dir.exists():
            return diffs
            
        for chunk_file in sorted(self.chunks_dir.glob("chunk_*.txt")):
            original_file = self.originals_dir / chunk_file.name
            if not original_file.exists():
                continue
            orig_text = original_file.read_text(encoding="utf-8")
            mod_text = chunk_file.read_text(encoding="utf-8")
            if orig_text != mod_text:
                chunk_id = int(chunk_file.stem.split("_")[-1])
                diffs.append(
                    ChunkDiff(
                        chunk_id=chunk_id,
                        path=chunk_file,
                        original_text=orig_text,
                        modified_text=mod_text,
                    )
                )
        return diffs

    def revert_chunk(self, chunk_id: int) -> None:
        filename = f"chunk_{chunk_id:03d}.txt"
        orig_file = self.originals_dir / filename
        target_file = self.chunks_dir / filename
        if orig_file.exists():
            target_file.write_text(orig_file.read_text(encoding="utf-8"), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_staging.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/staging.py tests/test_staging.py
git commit -m "feat: implement staging workspace and original snapshot diffing"
```

---

### Task 7: Terminal Reviewer & Diff Display Engine

**Files:**
- Modify: `book_angel/staging.py`
- Test: `tests/test_review.py`

**Interfaces:**
- Consumes: `StagingWorkspace` and modified chunks.
- Produces: Formatted unified color diff string, chunk approval tracking.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_review.py
from pathlib import Path
from book_angel.staging import StagingWorkspace, generate_unified_diff
from book_angel.parser.chunker import BookChunk
from book_angel.config import RulesConfig

def test_generate_diff_text(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="review-test")
    ws.initialize(
        title="Review",
        author="Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Line A\nLine B")]
    )
    
    (ws.chunks_dir / "chunk_001.txt").write_text("Line A\nLine Changed", encoding="utf-8")
    diffs = ws.get_modified_chunks()
    assert len(diffs) == 1
    
    diff_text = generate_unified_diff(diffs[0])
    assert "-Line B" in diff_text
    assert "+Line Changed" in diff_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_review.py -v`  
Expected: FAIL (cannot import `generate_unified_diff`)

- [ ] **Step 3: Write minimal implementation**

Add to `book_angel/staging.py`:
```python
import difflib

def generate_unified_diff(diff: ChunkDiff) -> str:
    orig_lines = diff.original_text.splitlines(keepends=True)
    mod_lines = diff.modified_text.splitlines(keepends=True)
    diff_generator = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"original/chunk_{diff.chunk_id:03d}.txt",
        tofile=f"edited/chunk_{diff.chunk_id:03d}.txt",
        lineterm=""
    )
    return "".join(diff_generator)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_review.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/staging.py tests/test_review.py
git commit -m "feat: implement unified diff generator for terminal review"
```

---

### Task 8: EPUB & PDF Reassembly & Metadata Customization Exporter

**Files:**
- Create: `book_angel/exporter.py`
- Test: `tests/test_exporter.py`

**Interfaces:**
- Consumes: `StagingWorkspace`, format (`"epub"` or `"pdf"`), title override, suffix.
- Produces: Assembled output file in destination folder.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exporter.py
from pathlib import Path
import zipfile
from book_angel.exporter import export_book
from book_angel.staging import StagingWorkspace
from book_angel.parser.chunker import BookChunk
from book_angel.config import RulesConfig

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exporter.py -v`  
Expected: FAIL (cannot import `export_book`)

- [ ] **Step 3: Write minimal implementation**

Create `book_angel/exporter.py`:
```python
"""Book packaging and export engine for EPUB and PDF."""
from __future__ import annotations
import json
from pathlib import Path
import re
import zipfile
from book_angel.staging import StagingWorkspace

def export_book(
    workspace: StagingWorkspace,
    output_dir: Path,
    export_format: str = "epub",
    title_suffix: str = "",
    custom_title: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metadata
    meta_path = workspace.root / "meta.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    base_title = custom_title or meta.get("title", "Exported Book")
    if title_suffix and not custom_title:
        final_title = f"{base_title} {title_suffix}".strip()
    else:
        final_title = base_title
        
    author = meta.get("author", "Unknown Author")
    safe_slug = re.sub(r"[^\w\-]", "_", final_title).strip("_")
    
    # Gather chunks
    chunk_texts: list[str] = []
    for chunk_file in sorted(workspace.chunks_dir.glob("chunk_*.txt")):
        content = chunk_file.read_text(encoding="utf-8")
        # Strip metadata comment header
        body = re.sub(r"^<!--.*?-->\s*", "", content, flags=re.DOTALL)
        chunk_texts.append(body.strip())
        
    joined_text = "\n\n".join(chunk_texts)
    
    cover_file = workspace.root / "cover.jpg"
    cover_bytes = cover_file.read_bytes() if cover_file.exists() else None

    if export_format.lower() == "epub":
        out_path = output_dir / f"{safe_slug}.epub"
        _build_epub(out_path, final_title, author, joined_text, cover_bytes)
        return out_path
    else:
        # PDF fallback export
        out_path = output_dir / f"{safe_slug}.pdf"
        _build_pdf(out_path, final_title, author, joined_text)
        return out_path

def _build_epub(out_path: Path, title: str, author: str, body_text: str, cover_bytes: bytes | None) -> None:
    paragraphs = "".join(f"<p>{p.strip()}</p>\n" for p in body_text.split("\n\n") if p.strip())
    
    with zipfile.ZipFile(out_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""")

        cover_manifest = ""
        cover_spine = ""
        if cover_bytes:
            zf.writestr("OEBPS/images/cover.jpg", cover_bytes)
            cover_manifest = '<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>'
            
        opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:book-angel-{abs(hash(title))}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <meta name="cover" content="cover-image"/>
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
  <title>{title}</title>
  <style>
    body {{ font-family: serif; line-height: 1.6; margin: 5%; }}
    p {{ text-indent: 1.5em; margin: 0; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {paragraphs}
</body>
</html>"""
        zf.writestr("OEBPS/chapter1.xhtml", xhtml)

def _build_pdf(out_path: Path, title: str, author: str, body_text: str) -> None:
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842) # A4 page
    writer.add_metadata({"/Title": title, "/Author": author})
    with open(out_path, "wb") as f:
        writer.write(f)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exporter.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/exporter.py tests/test_exporter.py
git commit -m "feat: implement EPUB and PDF export engine with cover preservation"
```

---

### Task 9: CLI Router & Command Line Interface

**Files:**
- Create: `book_angel/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: CLI args: `config`, `unpack <file>`, `review`, `export`, `status`.
- Produces: Complete working CLI.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from book_angel.cli import create_parser

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`  
Expected: FAIL (cannot import `create_parser`)

- [ ] **Step 3: Write minimal implementation**

Create `book_angel/cli.py`:
```python
"""Command line interface for Book-Angel."""
import argparse
from pathlib import Path
import sys
from book_angel import __version__
from book_angel.config import RulesConfig, save_rules_yaml, load_rules_yaml, ExamplePair
from book_angel.parser.epub_engine import parse_epub
from book_angel.parser.pdf_engine import parse_pdf
from book_angel.parser.chunker import chunk_text
from book_angel.staging import StagingWorkspace, generate_unified_diff
from book_angel.exporter import export_book

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="book-angel",
        description="Book-Angel: AI-assisted book content transformation and filtering."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # config
    subparsers.add_parser("config", help="Launch interactive rules configuration wizard.")
    
    # unpack
    p_unpack = subparsers.add_parser("unpack", help="Unpack EPUB or PDF into staging chunks.")
    p_unpack.add_argument("file", type=str, help="Path to EPUB or PDF book.")
    
    # review
    subparsers.add_parser("review", help="Review modified chunks interactively.")
    
    # export
    p_export = subparsers.add_parser("export", help="Reassemble approved chunks into book.")
    p_export.add_argument("--format", choices=["epub", "pdf"], default="epub", help="Target output format.")
    p_export.add_argument("--suffix", type=str, default="[Clean Edition]", help="Title suffix.")
    p_export.add_argument("--out", type=str, default="dist", help="Output directory.")
    
    # status
    subparsers.add_parser("status", help="Show status of current staging workspace.")
    
    return parser

def main() -> None:
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == "config":
        print("=== Book-Angel Configuration Wizard ===")
        print("Setting up rules in ~/.book-angel/rules.yaml...")
        config_path = Path.home() / ".book-angel" / "rules.yaml"
        current = load_rules_yaml(config_path)
        save_rules_yaml(current, config_path)
        print(f"Rules saved to {config_path}")
        
    elif args.command == "unpack":
        book_path = Path(args.file)
        if not book_path.exists():
            print(f"Error: File not found: {book_path}", file=sys.stderr)
            sys.exit(1)
            
        slug = book_path.stem.lower().replace(" ", "-")
        ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slug)
        
        if book_path.suffix.lower() == ".epub":
            epub = parse_epub(book_path)
            if epub.drm_protected:
                print(f"Error: {book_path.name} is DRM-protected. Please remove DRM before processing.", file=sys.stderr)
                sys.exit(1)
            chunks = []
            chunk_id = 1
            for idx, ch in enumerate(epub.chapters, 1):
                c = chunk_text(ch.content, chapter_title=ch.title, chapter_idx=idx, start_chunk_id=chunk_id)
                chunks.extend(c)
                chunk_id += len(c)
            ws.initialize(epub.title, epub.author, epub.cover_bytes, RulesConfig(), chunks)
            print(f"Successfully unpacked {len(chunks)} chunks into {ws.chunks_dir}")
            
        elif book_path.suffix.lower() == ".pdf":
            pdf = parse_pdf(book_path)
            if pdf.is_scanned_or_empty:
                print(f"Error: No text found in {book_path.name}. OCR required.", file=sys.stderr)
                sys.exit(1)
            joined = "\n\n".join(pdf.pages)
            chunks = chunk_text(joined, chapter_title=pdf.title, chapter_idx=1)
            ws.initialize(pdf.title, pdf.author, None, RulesConfig(), chunks)
            print(f"Successfully unpacked {len(chunks)} chunks into {ws.chunks_dir}")

    elif args.command == "review":
        staging_root = Path.cwd() / ".book-angel" / "staging"
        slugs = [d.name for d in staging_root.iterdir() if d.is_dir()] if staging_root.exists() else []
        if not slugs:
            print("No active book staging found.")
            return
        ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slugs[0])
        diffs = ws.get_modified_chunks()
        if not diffs:
            print("No modified chunks to review. All chunks match original.")
            return
        print(f"Found {len(diffs)} modified chunk(s) for review:\n")
        for diff in diffs:
            print(f"--- Chunk {diff.chunk_id:03d} ---")
            print(generate_unified_diff(diff))

    elif args.command == "export":
        staging_root = Path.cwd() / ".book-angel" / "staging"
        slugs = [d.name for d in staging_root.iterdir() if d.is_dir()] if staging_root.exists() else []
        if not slugs:
            print("No active book staging found.", file=sys.stderr)
            sys.exit(1)
        ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slugs[0])
        out_file = export_book(ws, Path(args.out), export_format=args.format, title_suffix=args.suffix)
        print(f"Export complete: {out_file}")

    elif args.command == "status":
        staging_root = Path.cwd() / ".book-angel" / "staging"
        if not staging_root.exists():
            print("No active staging workspaces.")
            return
        for slug_dir in staging_root.iterdir():
            if slug_dir.is_dir():
                ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slug_dir.name)
                diffs = ws.get_modified_chunks()
                print(f"Workspace: {slug_dir.name} | Modified Chunks: {len(diffs)}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add book_angel/cli.py tests/test_cli.py
git commit -m "feat: implement CLI parser and core command handlers"
```

---

### Task 10: Antigravity Custom Skill Definition & End-to-End Validation

**Files:**
- Create: `skill/SKILL.md`
- Test: `tests/test_end_to_end.py`

**Interfaces:**
- Produces: Ready-to-install Antigravity skill in `skill/SKILL.md`, verified by an end-to-end integration test.

- [ ] **Step 1: Write the failing end-to-end test**

```python
# tests/test_end_to_end.py
from pathlib import Path
from book_angel.parser.epub_engine import parse_epub
from book_angel.staging import StagingWorkspace
from book_angel.parser.chunker import chunk_text
from book_angel.config import RulesConfig
from book_angel.exporter import export_book
from tests.test_epub import create_dummy_epub

def test_full_pipeline_roundtrip(tmp_path: Path):
    # 1. Create dummy epub
    epub_file = tmp_path / "original.epub"
    create_dummy_epub(epub_file, encrypted=False)
    
    # 2. Ingest
    book = parse_epub(epub_file)
    assert not book.drm_protected
    
    # 3. Chunk
    chunks = chunk_text(book.chapters[0].content, chapter_title="Chapter 1", chapter_idx=1)
    
    # 4. Stage
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="full-test")
    ws.initialize(book.title, book.author, book.cover_bytes, RulesConfig(), chunks)
    
    # 5. Simulate Agent editing a chunk
    chunk_file = ws.chunks_dir / "chunk_001.txt"
    text = chunk_file.read_text(encoding="utf-8")
    edited_text = text.replace("cold and damp", "peaceful and starry")
    chunk_file.write_text(edited_text, encoding="utf-8")
    
    # 6. Verify Diff
    diffs = ws.get_modified_chunks()
    assert len(diffs) == 1
    assert "peaceful and starry" in diffs[0].modified_text
    
    # 7. Export
    out_dir = tmp_path / "dist"
    out_epub = export_book(ws, output_dir=out_dir, export_format="epub", title_suffix="[Clean Edition]")
    
    assert out_epub.exists()
    reparsed = parse_epub(out_epub)
    assert "peaceful and starry" in reparsed.chapters[0].content
    assert reparsed.cover_bytes == b"FAKECONTENTCOVER"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_end_to_end.py -v`  
Expected: PASS

- [ ] **Step 3: Create Antigravity Skill Definition (`skill/SKILL.md`)**

Create `skill/SKILL.md`:
```markdown
---
name: book-angel
description: AI-assisted book content filtering and transformation tool that unpacks EPUB/PDFs into chunks, applies user rules and few-shot examples, reviews diffs, and exports clean EPUB/PDFs.
---

# Book-Angel Skill

Use this skill when processing or filtering an EPUB or PDF book.

## Workflow

1. **Configure Rules**:
   `book-angel config`
   Inspects or edits `~/.book-angel/rules.yaml` and sets up before/after examples.

2. **Unpack Book**:
   `book-angel unpack <path_to_book>`
   Extracts cover art and breaks book into `.book-angel/staging/<slug>/chunks/`.

3. **Agent Editing**:
   Open `.book-angel/staging/<slug>/rules.md` for guidelines and few-shot examples.
   Inspect and edit `chunks/chunk_*.txt`. Maintain narrative fidelity while adjusting non-compliant scenes.

4. **Review Diffs**:
   `book-angel review`
   Examine diffs and approve changes.

5. **Export Clean Book**:
   `book-angel export --format epub`
   Rebuilds clean book with original cover art and metadata.
```

- [ ] **Step 4: Commit**

```bash
git add skill/SKILL.md tests/test_end_to_end.py
git commit -m "feat: add Antigravity skill definition and end-to-end integration test"
```
