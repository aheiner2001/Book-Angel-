from pathlib import Path
from book_angel.staging import StagingWorkspace, ChunkDiff, generate_unified_diff
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
    assert "--- original/chunk_001.txt\n" in diff_text
    assert "+++ edited/chunk_001.txt\n" in diff_text


def test_generate_diff_empty_when_identical():
    diff = ChunkDiff(
        chunk_id=2,
        path=Path("chunk_002.txt"),
        original_text="Same text\n",
        modified_text="Same text\n",
    )
    diff_text = generate_unified_diff(diff)
    assert diff_text == ""


def test_generate_diff_multiline_modifications():
    orig = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    mod = "Line 1\nLine 2 modified\nLine 3\nLine 4\nLine 5 added\n"
    diff = ChunkDiff(
        chunk_id=42,
        path=Path("chunk_042.txt"),
        original_text=orig,
        modified_text=mod,
    )
    diff_text = generate_unified_diff(diff)
    assert "--- original/chunk_042.txt\n" in diff_text
    assert "+++ edited/chunk_042.txt\n" in diff_text
    assert "-Line 2\n" in diff_text
    assert "+Line 2 modified\n" in diff_text
    assert "+Line 5 added\n" in diff_text


def test_staging_ignores_non_digit_chunk_files(tmp_path: Path):
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="review-test")
    ws.initialize(
        title="Review",
        author="Author",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Line A\nLine B")]
    )

    # Create non-digit chunk file and corresponding original
    (ws.chunks_dir / "chunk_backup.txt").write_text("modified backup", encoding="utf-8")
    (ws.originals_dir / "chunk_backup.txt").write_text("original backup", encoding="utf-8")

    diffs = ws.get_modified_chunks()
    # chunk_backup.txt should be safely skipped
    assert len(diffs) == 0
