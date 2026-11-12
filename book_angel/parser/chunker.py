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
        """Render chunk with standard HTML comment metadata header."""
        header = (
            f"<!-- chunk_id: {self.chunk_id:03d} | chapter: {self.chapter_idx} "
            f"| scene: {self.scene_idx} | title: {self.chapter_title} -->\n\n"
        )
        return header + self.body.strip() + "\n"


def chunk_text(
    text: str,
    chapter_title: str = "Chapter",
    chapter_idx: int = 1,
    max_words: int = 2500,
    start_chunk_id: int = 1,
) -> list[BookChunk]:
    """Split text into manageable chunks respecting chapter/scene boundaries and paragraph limits."""
    clean_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not clean_text:
        return []

    words = clean_text.split()
    if len(words) <= max_words:
        return [
            BookChunk(
                chunk_id=start_chunk_id,
                chapter_idx=chapter_idx,
                scene_idx=1,
                chapter_title=chapter_title,
                body=clean_text,
            )
        ]

    # Split by standard scene breaks if present
    scene_pattern = re.compile(
        r"\n\s*(?:\*{3,}|\*(?:\s*\*){2,}|-{3,}|-(?:\s*-){2,}|_{3,}|_(?:\s*_){2,}|\b___\b)\s*\n"
    )
    scenes = [s.strip() for s in scene_pattern.split(clean_text) if s.strip()]

    # If no scene breaks found, split by paragraphs
    if len(scenes) <= 1:
        paras = [p.strip() for p in re.split(r"\n\s*\n+", clean_text) if p.strip()]
        if len(paras) > 1:
            scenes = paras
        else:
            # Single unbroken block; split into word slices
            scenes = [
                " ".join(words[i : i + max_words])
                for i in range(0, len(words), max_words)
            ]

    chunks: list[BookChunk] = []
    current_chunk_words: list[str] = []
    current_pieces: list[str] = []
    scene_counter = 1
    current_chunk_id = start_chunk_id

    for scene in scenes:
        scene_words = scene.split()
        if len(current_chunk_words) + len(scene_words) > max_words and current_chunk_words:
            # Emit current
            body = "\n\n".join(current_pieces)
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
            current_pieces = [scene]
        else:
            current_chunk_words.extend(scene_words)
            current_pieces.append(scene)

    if current_pieces:
        chunks.append(
            BookChunk(
                chunk_id=current_chunk_id,
                chapter_idx=chapter_idx,
                scene_idx=scene_counter,
                chapter_title=chapter_title,
                body="\n\n".join(current_pieces),
            )
        )

    return chunks
