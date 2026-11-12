# 📖 Book-Angel

**Book-Angel** is an intelligent book transformation and filtering companion designed to run alongside AI agents (such as Google Antigravity CLI and Cursor IDE). It allows you to safely adapt EPUB and PDF books according to custom content guidelines (e.g., softening graphic romance/kissing, reducing violence or gore, omitting specific themes) while preserving original cover art, typography, and book formatting.

---

## 🚀 Quick Setup & Installation

### 1. Requirements
- Python 3.10+
- Terminal / CLI (macOS, Linux, or Windows)
- (Optional) [Google Antigravity CLI](https://github.com) or [Cursor IDE](https://www.cursor.com)

### 2. Install the Python CLI
Clone and install the package locally in editable mode:

```bash
cd Book-Angel-
pip install -e .
```

Verify the installation:
```bash
book-angel --version
# Output: book-angel 0.1.0
```

### 3. Install as an Antigravity Custom Skill (Optional)
To use Book-Angel directly within your Antigravity agent terminal (`agy`), copy or link the skill:

```bash
mkdir -p ~/.gemini/antigravity-cli/skills/book-angel
cp skill/SKILL.md ~/.gemini/antigravity-cli/skills/book-angel/
```

Now you can invoke `/book-angel` directly in your agent chat!

---

## 🛠️ Complete 5-Step Workflow

```text
[Input Book (.epub / .pdf)]
           │
           ▼
1. book-angel config        ──► Sets guidelines & before/after examples
           │
           ▼
2. book-angel unpack <file> ──► Extracts cover, styles, & chunks (<2,500 words)
           │
           ▼
3. Agent Processing         ──► Antigravity or Cursor Agent rewrites chunks
           │
           ▼
4. book-angel review        ──► Approve, reject, or edit diffs interactively
           │
           ▼
5. book-angel export        ──► Packages final EPUB / PDF with original cover
```

---

### Step 1: Configure Your Rules & Examples

Run the configuration wizard to set your default guidelines:
```bash
book-angel config
```

This creates or updates `~/.book-angel/rules.yaml`. You can open this file anytime to customize your policy levels, omitted topics, and few-shot examples:

```yaml
romance_level: mild
violence_level: adventure
language_level: cleaned
omitted_topics:
  - passionate or explicit intimacy
  - graphic gore
custom_rules:
  - Keep character banter and humor intact.
examples:
  - before: "He pulled her close, kissing her passionately on the lips against the door."
    after: "He smiled softly and gave her a gentle kiss on the cheek before stepping back."
```

> **Tip:** Adding **before & after examples** teaches the AI the exact tone, replacement style, and restraint you prefer!

---

### Step 2: Unpack Your Book

Point Book-Angel to any EPUB or PDF file:

```bash
book-angel unpack "path/to/my_book.epub"
```

What this does automatically:
- Creates an isolated staging folder: `.book-angel/staging/<book-name>/`
- Preserves the original cover image (`cover.jpg`)
- Splits the text into natural chapters & scene chunks (`chunks/chunk_001.txt`, `chunk_002.txt`...)
- Saves pristine, untouched copies in `.originals/` so changes can always be diffed or rolled back

---

### Step 3: Run the AI Agent to Edit Chunks

You can let the AI edit your book using either **Antigravity CLI** or **Cursor IDE**:

#### Option A: In Antigravity CLI (`agy`)
Simply prompt the agent:
> *"Process the unpacked book in staging according to rules.md"*

The agent will read `.book-angel/staging/<book-slug>/rules.md` and edit the chunk files in `chunks/`.

#### Option B: In Cursor IDE
1. Open the `Book-Angel-` folder in Cursor.
2. In Composer / Chat (`Cmd + I` or `Cmd + L`), prompt the agent:
   > *"Review all chunks in `.book-angel/staging/<book-slug>/chunks/` and modify them to follow the guidelines in `rules.md`."*
3. The agent edits each chunk file right inside your workspace.

---

### Step 4: Review Diffs & Approve Changes

Book-Angel provides two ways to inspect changes:

#### 1. Interactive Terminal Review
Run:
```bash
book-angel review
```
This shows syntax-highlighted terminal diffs for each modified chunk, allowing you to review line-by-line additions (`+`) and removals (`-`).

#### 2. Visual Side-by-Side in Cursor / VS Code
Because original files are preserved in `.originals/`, you can also open any chunk side-by-side or inspect changes using your editor's visual Git / Diff viewer.

---

### Step 5: Export the Clean Book

When you're ready, rebuild the book into your preferred format:

```bash
# Export as EPUB (Recommended - preserves responsive reading on Kindle / Apple Books / Kobo)
book-angel export --format epub --suffix "[Clean Edition]"

# Or export as PDF
book-angel export --format pdf --suffix "[Clean Edition]"
```

Your clean edition will be saved in `dist/` (e.g., `dist/My_Book_Clean_Edition.epub`) with:
- ✅ Original cover art preserved
- ✅ Internal typography, font styles, and layout intact
- ✅ Updated book title and clean metadata

---

## 📋 CLI Commands Reference

| Command | Description |
|---|---|
| `book-angel config` | Run the interactive setup wizard for rules and examples. |
| `book-angel unpack <file>` | Extract EPUB/PDF into structured staging chunks and save cover art. |
| `book-angel status` | Check active staging workspaces and modified chunk counts. |
| `book-angel review` | Walk through modified chunks in the terminal with colored diffs. |
| `book-angel export` | Reassemble approved chunks into EPUB or PDF. |
| `book-angel --version` | Display installed version. |

### Optional Export Flags:
- `--format`: Output format: `epub` (default) or `pdf`.
- `--suffix`: Subtitle appended to book title (default: `"[Clean Edition]"`).
- `--out`: Destination directory (default: `dist`).

---

## 💡 Troubleshooting & Edge Cases

- **DRM-Protected EPUBs**: If an EPUB has Adobe, Apple, or Amazon DRM encryption, `book-angel unpack` will display an informative message explaining that DRM must be removed prior to processing.
- **Scanned / Image-Only PDFs**: If a PDF contains no selectable text (scanned page images), Book-Angel alerts you that OCR text extraction is required before chunking.
- **Rolling Back a Chunk**: If an AI rewrite isn't what you wanted, you can revert any chunk back to its original state before exporting.

---

## 🧪 Running Tests

To verify that all components are working properly on your system:

```bash
pytest -v
```

All 63 unit and end-to-end integration tests should pass in under 1 second.
