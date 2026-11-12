---
name: book-angel
description: AI-assisted book content filtering, character adaptation, and transformation tool that unpacks EPUB/PDFs into chunks, applies user rules and few-shot examples, reviews diffs, and exports clean EPUB/PDFs.
---

# Book-Angel Skill

Use this skill when the user asks to filter, clean, adapt characters, or process an EPUB or PDF book.

## Quick Workflow

1. **Unpack Book**:
   Run `book-angel unpack` (or user provides book). Chunks are placed in `.book-angel/staging/<book-slug>/chunks/`.
   Rules are compiled into `.book-angel/staging/<book-slug>/rules.md`.

2. **Agent Action (Automated Processing)**:
   - Read `.book-angel/staging/<book-slug>/rules.md`.
   - Iterate through `chunks/chunk_*.txt`:
     - Inspect each chunk against the policy levels (romance, violence, language), omitted topics, and character mappings.
     - If non-compliant passages or character names (e.g. Julian -> Julia) are found, edit the file in place.
     - Keep all non-conflicting prose, tone, formatting, and HTML/scene tags 100% identical.

3. **Diff Review & Verification**:
   - The user inspects diffs using `book-angel review` or visually in Cursor / Git source control.

4. **Export Clean Edition**:
   - Run `book-angel export --format epub` (or `--format pdf`).
   - Clean book is saved directly to `~/Downloads/`.
