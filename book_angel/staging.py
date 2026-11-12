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

