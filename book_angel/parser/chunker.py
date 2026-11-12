"""Text chunking logic for Book-Angel."""
from __future__ import annotations
from dataclasses import dataclass
import re

SCENE_SPLIT_PATTERN = re.compile(
    r"(?:^|\n)[ \t]*((?:\*{3,}|\*(?:[ \t]*\*){2,}|-{3,}|-(?:[ \t]*-){2,}|_{3,}|_(?:[ \t]*_){2,}|\b___\b))[ \t]*(?:\n|$)"
)


@dataclass
class BookChunk:
    chunk_id: int
    chapter_idx: int
    scene_idx: int
    chapter_title: str
    body: str

    @property
    def header(self) -> str:
        """Render standard HTML comment metadata header."""
        return (
            f"<!-- chunk_id: {self.chunk_id:03d} | chapter: {self.chapter_idx} "
            f"| scene: {self.scene_idx} | title: {self.chapter_title} -->\n\n"
        )

    @property
    def chapter_index(self) -> int:
        """Alias for chapter_idx."""
        return self.chapter_idx

    @chapter_index.setter
    def chapter_index(self, value: int) -> None:
        self.chapter_idx = value

    @property
    def scene_index(self) -> int:
        """Alias for scene_idx."""
        return self.scene_idx

    @scene_index.setter
    def scene_index(self, value: int) -> None:
        self.scene_idx = value

    def render(self) -> str:
        """Render chunk with standard HTML comment metadata header."""
        return self.header + self.body.strip() + "\n"


@dataclass
class _AtomicUnit:
    text: str
    delimiter_before: str | None = None


def chunk_text(
    text: str,
    chapter_title: str = "Chapter",
    chapter_idx: int = 1,
    max_words: int = 2500,
    start_chunk_id: int = 1,
    max_words_per_chunk: int | None = None,
) -> list[BookChunk]:
    """Split text into manageable chunks respecting chapter/scene boundaries and paragraph limits."""
    if max_words_per_chunk is not None:
        max_words = max_words_per_chunk

    if max_words <= 0:
        raise ValueError(f"max_words must be greater than 0, got {max_words}")

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

    # Split into scenes and delimiters
    raw_parts = SCENE_SPLIT_PATTERN.split(clean_text)
    scenes: list[tuple[str, str | None]] = []
    if len(raw_parts) == 1:
        if raw_parts[0].strip():
            scenes.append((raw_parts[0].strip(), None))
    else:
        current_delim: str | None = None
        for i, part in enumerate(raw_parts):
            if i % 2 == 1:
                current_delim = part.strip()
            else:
                s_text = part.strip()
                if s_text:
                    scenes.append((s_text, current_delim))
                    current_delim = None

    # Subdivide scenes hierarchically into atomic units
    units: list[_AtomicUnit] = []
    for scene_text, delim_before in scenes:
        scene_words = scene_text.split()
        scene_units: list[str] = []
        if len(scene_words) <= max_words:
            scene_units.append(scene_text)
        else:
            raw_paras = [p.strip() for p in re.split(r"\n\s*\n+", scene_text) if p.strip()]
            if not raw_paras:
                raw_paras = [scene_text]
            for p in raw_paras:
                p_words = p.split()
                if len(p_words) <= max_words:
                    scene_units.append(p)
                else:
                    for i in range(0, len(p_words), max_words):
                        scene_units.append(" ".join(p_words[i : i + max_words]))

        for i, u_text in enumerate(scene_units):
            delim = delim_before if i == 0 else None
            units.append(_AtomicUnit(text=u_text, delimiter_before=delim))

    # Accumulate atomic units into chunks without exceeding max_words
    chunks: list[BookChunk] = []
    current_chunk_words = 0
    current_pieces: list[str] = []
    current_chunk_id = start_chunk_id
    scene_counter = 1

    def emit_chunk() -> None:
        nonlocal current_chunk_id, scene_counter, current_chunk_words, current_pieces
        if not current_pieces:
            return
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
        current_pieces = []
        current_chunk_words = 0

    for unit in units:
        u_words = len(unit.text.split())
        delim = unit.delimiter_before
        delim_words = len(delim.split()) if delim else 0

        if not current_pieces:
            current_pieces.append(unit.text)
            current_chunk_words = u_words
        else:
            needed = (delim_words + u_words) if delim else u_words
            if current_chunk_words + needed <= max_words:
                if delim:
                    current_pieces.append(delim)
                current_pieces.append(unit.text)
                current_chunk_words += needed
            else:
                emit_chunk()
                current_pieces.append(unit.text)
                current_chunk_words = u_words

    emit_chunk()
    return chunks
