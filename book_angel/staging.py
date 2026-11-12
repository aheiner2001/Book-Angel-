"""Staging workspace manager for Book-Angel."""
from __future__ import annotations
from dataclasses import dataclass
import difflib
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
    def __init__(self, base_dir: Path | str, book_slug: str):
        self.base_dir = Path(base_dir)
        self.book_slug = book_slug
        self.root = self.base_dir / ".book-angel" / "staging" / book_slug
        self.chunks_dir = self.root / "chunks"
        self.originals_dir = self.root / ".originals"

    def initialize(
        self,
        title: str,
        author: str,
        cover_bytes: bytes | None,
        rules: RulesConfig,
        chunks: list[BookChunk],
        source_file: Path | str | None = None,
        chapter_map: dict | None = None,
    ) -> None:
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.originals_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        meta = {
            "title": title,
            "author": author,
            "chunk_count": len(chunks),
        }

        # If source file provided, copy to workspace and record format
        if source_file:
            src_p = Path(source_file)
            if src_p.exists():
                ext = src_p.suffix.lstrip(".").lower()
                meta["source_format"] = ext
                target_name = "source.epub" if ext == "epub" else src_p.name
                meta["source_file"] = target_name
                dest = self.root / target_name
                if dest.resolve() != src_p.resolve():
                    import shutil
                    shutil.copy2(src_p, dest)

        if chapter_map:
            meta["chapter_map"] = chapter_map

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
                if not chunk_file.stem.split("_")[-1].isdigit():
                    continue
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


def generate_unified_diff(diff: ChunkDiff) -> str:
    """Generate a formatted unified diff string comparing original vs modified chunk text."""
    orig_lines = diff.original_text.splitlines(keepends=True)
    mod_lines = diff.modified_text.splitlines(keepends=True)
    orig_lines = [line if line.endswith("\n") else line + "\n" for line in orig_lines]
    mod_lines = [line if line.endswith("\n") else line + "\n" for line in mod_lines]
    diff_generator = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"original/chunk_{diff.chunk_id:03d}.txt",
        tofile=f"edited/chunk_{diff.chunk_id:03d}.txt",
    )
    return "".join(diff_generator)


def extract_change_snippets(diff: ChunkDiff, max_snippets_per_chunk: int = 5) -> list[tuple[str, str]]:
    """Extract concise clipped 'before' and 'after' text snippets highlighting differences."""
    import re

    orig_clean = re.sub(r"^<!--.*?-->\s*", "", diff.original_text, flags=re.DOTALL).strip()
    mod_clean = re.sub(r"^<!--.*?-->\s*", "", diff.modified_text, flags=re.DOTALL).strip()

    orig_lines = [l.strip() for l in orig_clean.splitlines() if l.strip()]
    mod_lines = [l.strip() for l in mod_clean.splitlines() if l.strip()]

    matcher = difflib.SequenceMatcher(None, orig_lines, mod_lines)
    opcodes = matcher.get_opcodes()
    snippets: list[tuple[str, str]] = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue

        b_text = " ".join(orig_lines[i1:i2])
        a_text = " ".join(mod_lines[j1:j2])

        if tag == "replace":
            w1 = b_text.split()
            w2 = a_text.split()
            wm = difflib.SequenceMatcher(None, w1, w2)
            sub_ops = [op for op in wm.get_opcodes() if op[0] != "equal"]
            if sub_ops:
                s1 = max(0, sub_ops[0][1] - 3)
                e1 = min(len(w1), sub_ops[-1][2] + 3)
                s2 = max(0, sub_ops[0][3] - 3)
                e2 = min(len(w2), sub_ops[-1][4] + 3)

                c1 = ("... " if s1 > 0 else "") + " ".join(w1[s1:e1]) + (" ..." if e1 < len(w1) else "")
                c2 = ("... " if s2 > 0 else "") + " ".join(w2[s2:e2]) + (" ..." if e2 < len(w2) else "")
                snippets.append((c1, c2))
            else:
                snippets.append((b_text, a_text))
        elif tag == "delete":
            w1 = b_text.split()
            c1 = " ".join(w1[:15]) + (" ..." if len(w1) > 15 else "")
            snippets.append((c1, "[removed]"))
        elif tag == "insert":
            w2 = a_text.split()
            c2 = " ".join(w2[:15]) + (" ..." if len(w2) > 15 else "")
            snippets.append(("[added]", c2))

        if len(snippets) >= max_snippets_per_chunk:
            break

    # Fallback if line-based matching produced nothing but texts differ
    if not snippets and orig_clean != mod_clean:
        w1 = orig_clean.split()
        w2 = mod_clean.split()
        wm = difflib.SequenceMatcher(None, w1, w2)
        sub_ops = [op for op in wm.get_opcodes() if op[0] != "equal"]
        if sub_ops:
            s1 = max(0, sub_ops[0][1] - 3)
            e1 = min(len(w1), sub_ops[-1][2] + 3)
            s2 = max(0, sub_ops[0][3] - 3)
            e2 = min(len(w2), sub_ops[-1][4] + 3)
            c1 = ("... " if s1 > 0 else "") + " ".join(w1[s1:e1]) + (" ..." if e1 < len(w1) else "")
            c2 = ("... " if s2 > 0 else "") + " ".join(w2[s2:e2]) + (" ..." if e2 < len(w2) else "")
            snippets.append((c1, c2))

    return snippets


def format_change_summary(diffs: list[ChunkDiff]) -> str:
    """Format a clean, readable summary of all clipped changes across modified chunks."""
    if not diffs:
        return "No changes made."

    lines: list[str] = [
        "=" * 65,
        f"📝 SUMMARY OF CHANGES MADE ({len(diffs)} chunk(s) modified)",
        "=" * 65,
    ]

    for diff in diffs:
        snippets = extract_change_snippets(diff)
        lines.append(f"\n• Chunk {diff.chunk_id:03d} ({diff.path.name}):")
        if not snippets:
            lines.append("  (Formatting or whitespace adjustments)")
        else:
            for idx, (before_clip, after_clip) in enumerate(snippets, 1):
                if len(snippets) > 1:
                    lines.append(f"  Change {idx}:")
                lines.append(f"    - Before: \"{before_clip}\"")
                lines.append(f"    + After:  \"{after_clip}\"")

    lines.append("\n" + "=" * 65)
    return "\n".join(lines)

