"""Tests for the smart chunker and scene boundary management."""
from __future__ import annotations
import pytest
from book_angel.parser.chunker import BookChunk, chunk_text


def test_chunk_short_text():
    """Verify that text shorter than max_words produces a single chunk."""
    text = "Short chapter content with a few words."
    chunks = chunk_text(text, chapter_title="Chapter 1", chapter_idx=1, max_words=100)
    assert len(chunks) == 1
    assert chunks[0].chapter_idx == 1
    assert chunks[0].chunk_id == 1
    assert chunks[0].scene_idx == 1
    assert "Short chapter content" in chunks[0].body
    assert "<!-- chunk_id: 001" in chunks[0].render()


def test_chunk_splits_long_text_at_scene_break():
    """Verify that long text splits cleanly at standard scene breaks (***)."""
    scene1 = "Word " * 60 + "\n\n***\n\n"
    scene2 = "Other " * 60
    full_text = scene1 + scene2
    chunks = chunk_text(full_text, chapter_title="Chapter 2", chapter_idx=2, max_words=50)
    assert len(chunks) >= 2
    assert "Word" in chunks[0].body
    assert "Other" in chunks[1].body


def test_chunk_various_scene_separators():
    """Verify that * * *, ---, - - -, and ___ are recognized as scene breaks."""
    separators = ["\n\n* * *\n\n", "\n\n---\n\n", "\n\n- - -\n\n", "\n\n___\n\n"]
    for sep in separators:
        s1 = "Alpha " * 60
        s2 = "Beta " * 60
        text = s1 + sep + s2
        chunks = chunk_text(text, chapter_title="Chapter Test", chapter_idx=1, max_words=50)
        assert len(chunks) >= 2, f"Failed to split on separator {sep!r}"
        assert "Alpha" in chunks[0].body
        assert "Beta" in chunks[1].body


def test_chunk_splits_at_paragraphs_when_no_scene_breaks():
    """Verify that chapters exceeding max_words without scene breaks split at paragraph boundaries."""
    p1 = "First paragraph content. " * 30
    p2 = "Second paragraph content. " * 30
    p3 = "Third paragraph content. " * 30
    full_text = f"{p1}\n\n{p2}\n\n{p3}"
    chunks = chunk_text(full_text, chapter_title="Chapter 3", chapter_idx=3, max_words=50)
    assert len(chunks) >= 3
    assert "First paragraph content." in chunks[0].body
    assert "Second paragraph content." in chunks[1].body
    assert "Third paragraph content." in chunks[2].body


def test_chunk_single_very_long_paragraph():
    """Verify that an oversized paragraph with no breaks is split by word count."""
    long_para = "Unbroken " * 120
    chunks = chunk_text(long_para, chapter_title="Long Para", chapter_idx=1, max_words=50)
    assert len(chunks) == 3
    for chunk in chunks:
        assert len(chunk.body.split()) <= 50


def test_chunk_sequential_chunk_ids_and_start_chunk_id():
    """Verify that chunk_id increments sequentially from start_chunk_id."""
    scene1 = "Section One " * 40 + "\n\n***\n\n"
    scene2 = "Section Two " * 40
    chunks = chunk_text(scene1 + scene2, chapter_title="Ch 4", chapter_idx=4, max_words=30, start_chunk_id=10)
    assert len(chunks) >= 2
    assert chunks[0].chunk_id == 10
    assert chunks[1].chunk_id == 11


def test_chunk_empty_or_whitespace_text():
    """Verify that empty or whitespace-only text returns an empty list."""
    assert chunk_text("") == []
    assert chunk_text("   \n\t  ") == []


def test_chunk_render_header_format():
    """Verify exact comment header rendering format."""
    chunk = BookChunk(
        chunk_id=42,
        chapter_idx=3,
        scene_idx=2,
        chapter_title="The Castle",
        body="Harker arrived at the gate.",
    )
    rendered = chunk.render()
    expected = (
        "<!-- chunk_id: 042 | chapter: 3 | scene: 2 | title: The Castle -->\n\n"
        "Harker arrived at the gate.\n"
    )
    assert rendered == expected


def test_parser_init_exports():
    """Verify BookChunk and chunk_text are exported in book_angel.parser."""
    import book_angel.parser as parser
    assert hasattr(parser, "BookChunk")
    assert hasattr(parser, "chunk_text")
    assert "BookChunk" in parser.__all__
    assert "chunk_text" in parser.__all__
