from pathlib import Path
from book_angel.staging import StagingWorkspace, ChunkDiff
from book_angel.parser.chunker import BookChunk
from book_angel.config import RulesConfig


def test_staging_initialization(tmp_path: Path):
    workspace = StagingWorkspace(base_dir=tmp_path, book_slug="dracula")
    workspace.initialize(
        title="Dracula",
        author="Bram Stoker",
        cover_bytes=b"COVERIMG",
        rules=RulesConfig(romance_level="mild"),
        chunks=[
            BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Original text here.")
        ]
    )

    assert (workspace.root / "meta.json").exists()
    assert (workspace.root / "cover.jpg").exists()
    assert (workspace.chunks_dir / "chunk_001.txt").exists()
    assert (workspace.originals_dir / "chunk_001.txt").exists()
    assert (workspace.root / "rules.md").exists()

    # Check no diff initially
    diffs = workspace.get_modified_chunks()
    assert len(diffs) == 0

    # Modify chunk
    (workspace.chunks_dir / "chunk_001.txt").write_text("Modified text here.", encoding="utf-8")
    diffs_after = workspace.get_modified_chunks()
    assert len(diffs_after) == 1
    assert diffs_after[0].chunk_id == 1
    assert diffs_after[0].modified_text == "Modified text here."
    assert "Original text here." in diffs_after[0].original_text


def test_staging_revert_chunk(tmp_path: Path):
    workspace = StagingWorkspace(base_dir=tmp_path, book_slug="frankenstein")
    chunk = BookChunk(chunk_id=42, chapter_idx=2, scene_idx=1, chapter_title="Ch 2", body="It was on a dreary night.")
    workspace.initialize(
        title="Frankenstein",
        author="Mary Shelley",
        cover_bytes=None,
        rules=RulesConfig(),
        chunks=[chunk]
    )

    # Cover should not exist when cover_bytes is None
    assert not (workspace.root / "cover.jpg").exists()

    # Modify chunk 42
    target_file = workspace.chunks_dir / "chunk_042.txt"
    target_file.write_text("Altered text.", encoding="utf-8")
    assert len(workspace.get_modified_chunks()) == 1

    # Revert chunk 42
    workspace.revert_chunk(42)
    assert len(workspace.get_modified_chunks()) == 0
    assert target_file.read_text(encoding="utf-8") == chunk.render()

    # Reverting non-existent chunk should not raise
    workspace.revert_chunk(999)


def test_staging_multiple_chunks_and_selective_diff(tmp_path: Path):
    workspace = StagingWorkspace(base_dir=str(tmp_path), book_slug="multi")
    chunks = [
        BookChunk(chunk_id=1, chapter_idx=1, scene_idx=1, chapter_title="Ch 1", body="Chunk 1 body"),
        BookChunk(chunk_id=2, chapter_idx=1, scene_idx=2, chapter_title="Ch 1", body="Chunk 2 body"),
        BookChunk(chunk_id=3, chapter_idx=2, scene_idx=1, chapter_title="Ch 2", body="Chunk 3 body"),
    ]
    workspace.initialize(
        title="Multi Chunk Book",
        author="Author",
        cover_bytes=b"IMG",
        rules=RulesConfig(),
        chunks=chunks
    )

    # Modify chunk 2 and chunk 3
    (workspace.chunks_dir / "chunk_002.txt").write_text("Modified 2", encoding="utf-8")
    (workspace.chunks_dir / "chunk_003.txt").write_text("Modified 3", encoding="utf-8")

    diffs = workspace.get_modified_chunks()
    assert len(diffs) == 2
    assert [d.chunk_id for d in diffs] == [2, 3]

    # Revert only chunk 2
    workspace.revert_chunk(2)
    diffs_after = workspace.get_modified_chunks()
    assert len(diffs_after) == 1
    assert diffs_after[0].chunk_id == 3


def test_staging_uninitialized_directory(tmp_path: Path):
    workspace = StagingWorkspace(base_dir=tmp_path, book_slug="nonexistent")
    assert workspace.get_modified_chunks() == []
