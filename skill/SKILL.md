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
