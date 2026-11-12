# Design Specification: Book-Angel

**Date:** 2026-11-11  
**Status:** Approved  
**Project:** Book-Angel (`/Users/aaronheiner/Book-Angel-`)

---

## 1. Executive Summary & Purpose

**Book-Angel** is an intelligent book transformation and filtering system designed to run as a CLI tool and an agent companion (supporting both Antigravity agent workflows and Cursor IDE). It allows readers to ingest EPUB and PDF books, break them down into structured manageable chunks, apply customizable narrative filtering rules (e.g., toning down passionate kissing/sensuality, omitting specified themes, reducing graphic gore/violence), interactively inspect and approve diffs, and reassemble the final work back into an EPUB or PDF with original cover art, styling, and metadata preserved.

---

## 2. Key Requirements & Capabilities

1. **Dual-Environment Compatibility**: Operates seamlessly in standard terminal shells, within the Antigravity CLI via an installed custom skill, and within Cursor/VS Code.
2. **Staging & File-Based Loop**: Decouples heavy file processing from AI reasoning. Unpacks books into local chunks for the agent to inspect and edit; tracks changes against pristine originals without requiring proprietary API tokens.
3. **Smart Ingestion & Cover Preservation**:
   - Parses EPUB archives, preserves internal CSS, font stylesheets, and original cover art.
   - Extracts PDF text and captures first-page cover art.
   - Detects DRM protection and corrupted archives with friendly diagnostics.
4. **Intelligent Chunking**: Splits books at natural chapter boundaries and scene breaks (~2,500 words per chunk max) so narrative context remains coherent.
5. **Configurable Rules & Few-Shot Examples**:
   - Interactive configuration wizard (`book-angel config`) generating `rules.yaml` and formatted `rules.md`.
   - Supports preset categories (Romance, Violence, Language, Topics) and freeform user rules.
   - Supports custom before-and-after text examples to guide the AI's nuance and tone.
6. **Dual Diff Review Experience**:
   - Terminal interactive reviewer (`book-angel review`) for line-by-line diff approval (`[A]pprove`, `[R]eject`, `[E]dit`, `[S]kip`).
   - Native editor git/diff support in Cursor/VS Code.
7. **Customizable Export**:
   - Reassembles approved chunks back into EPUB or PDF.
   - Prompts for format selection, cover art confirmation, and title/description adjustments (e.g., adding `[Clean Edition]`).

---

## 3. System Architecture & Project Layout

```text
Book-Angel-/
├── pyproject.toml              # Modern Python build & CLI entrypoint (`book-angel`)
├── book_angel/
│   ├── __init__.py
│   ├── cli.py                  # CLI command dispatch: config, unpack, review, export, status
│   ├── config.py               # Rules setup wizard, YAML/MD serialization, few-shot examples
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── epub_engine.py      # EPUB reader, spine walker, cover extractor & repacker
│   │   ├── pdf_engine.py       # PDF reader & cover/text extractor
│   │   └── chunker.py          # Scene & chapter chunking logic (<2,500 words per chunk)
│   ├── staging.py              # Staging workspace manager, original snapshotting, diff engine
│   └── exporter.py             # EPUB & PDF rebuilder with cover retention and metadata updates
├── skill/
│   └── SKILL.md                # Antigravity skill definition for agent-driven execution
├── tests/
│   ├── test_epub.py            # EPUB unpack/repack and cover preservation tests
│   ├── test_chunking.py        # Chunk boundary tests
│   ├── test_diff.py            # Review and diff tracking tests
│   └── test_config.py          # Rules wizard and parser tests
└── docs/
    └── superpowers/specs/      # Project specifications
```

---

## 4. Staging Workspace Specification

Each book processed is assigned a slugified project folder inside `.book-angel/staging/<book-slug>/`:

```text
.book-angel/staging/<book-slug>/
├── meta.json               # Book metadata (original title, author, cover path, spine order)
├── cover.jpg               # Extracted cover art asset (preserved for export)
├── rules.md                # Active rules and few-shot examples for agent context
├── chunks/                 # Active chunk files being edited
│   ├── chunk_001_ch01.txt
│   ├── chunk_002_ch01.txt
│   └── ...
└── .originals/             # Pristine, unmodified snapshots used to compute diffs
    ├── chunk_001_ch01.txt
    ├── chunk_002_ch01.txt
    └── ...
```

---

## 5. Detailed Component Workflows

### 5.1 Configuration & Rules Engine (`config.py`)
- **CLI Wizard**: `book-angel config`
  - Guides the user through presets:
    - *Romance & Sensuality*: (e.g., Mild kissing only, fade-to-black on intimate scenes).
    - *Content & Themes*: (e.g., Exclude specific themes or mentions).
    - *Violence & Gore*: (e.g., Reduce graphic gore, keep action adventure-oriented).
    - *Language & Profanity*: (e.g., Cleaned, PG, custom substitutions).
    - *Custom Guidelines*: Freeform text rules.
    - *Before/After Examples*: Allows entering or pasting sample original text and its desired rewritten version.
  - Writes to `~/.book-angel/rules.yaml` (global defaults) and copies to project staging as `rules.md`.

### 5.2 Ingestion & Chunking (`epub_engine.py`, `pdf_engine.py`, `chunker.py`)
- **EPUB Parser**:
  - Reads `content.opf` to locate manifest items and spine order.
  - Extracts cover image by scanning `properties="cover-image"`, `<meta name="cover">`, or fallback image names.
  - Retains all CSS files, fonts, and XHTML packaging structure.
- **PDF Parser**:
  - Extracts text per page/chapter using `pymupdf`/`pypdf`.
  - Extracts Page 1 as high-res cover art.
- **Chunker**:
  - Splits at natural chapter boundaries.
  - If a chapter exceeds ~2,500 words, subdivides at scene transitions (`***`, section dividers, or paragraph endings).
  - Prepends metadata header to each chunk:
    ```text
    <!-- chunk_id: 001 | chapter: 1 | scene: 1 | title: Chapter 1 -->
    ```
- **Diagnostics & Edge Cases**:
  - If `META-INF/encryption.xml` is present, halts with a clear explanation of DRM restrictions.
  - If PDF has no extractable text, warns that OCR is required.
  - If EPUB archive is corrupted, provides clear actionable recovery guidance.

### 5.3 Agent Workflow & Diff Approval (`staging.py`, `cli.py`)
- **Agent Step**:
  - The Antigravity skill or Cursor agent reads `rules.md` and modifies `chunks/chunk_*.txt`.
  - Content not violating rules is kept unchanged.
- **Review Step**: `book-angel review`
  - Scans `chunks/` vs `.originals/`.
  - For each modified chunk, displays syntax-highlighted diff (ANSI green/red).
  - Prompts user:
    - `[A]` Approve change.
    - `[R]` Reject change (restores `.originals/` version).
    - `[E]` Open in editor for manual touch-up.
    - `[S]` Skip for later.
  - Compatible with Cursor Git diff viewer for visual side-by-side inspection.

### 5.4 Reassembly & Export (`exporter.py`)
- **Pre-Flight Validation**: Warns if any modified chunks remain unreviewed.
- **Export Wizard Prompts**:
  - Target format: EPUB (default) or PDF.
  - Cover art: Keep original extracted cover image (default) or specify replacement.
  - Title & Metadata: Keep original, append suffix (e.g. `[Clean Edition]`), or specify custom title/description.
- **EPUB Packaging**:
  - Injects approved chunk text into original XHTML templates.
  - Packages valid EPUB (uncompressed `mimetype` at offset 0, valid manifest, spine, and navigation).
  - Output written to `dist/<title>_<suffix>.epub`.
- **PDF Packaging**:
  - Formats approved text with typography margins, headers, pagination, and embeds cover art on page 1.
  - Output written to `dist/<title>_<suffix>.pdf`.

---

## 6. Testing Strategy

1. **Unit Tests**:
   - `test_config.py`: Test YAML loading, wizard defaults, before/after example serialization.
   - `test_chunking.py`: Test chapter boundary preservation, long chapter subdivision, context header integrity.
   - `test_epub.py`: Test cover image identification, XHTML text replacement, style preservation, valid zip packaging.
   - `test_diff.py`: Test diff calculation, chunk revert, chunk approval state tracking.
2. **Integration Tests**:
   - Full roundtrip with sample EPUB and PDF files: unpack $\rightarrow$ modify sample chunk $\rightarrow$ review/approve $\rightarrow$ export and verify file readability.
