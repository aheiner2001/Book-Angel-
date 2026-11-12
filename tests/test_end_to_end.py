from pathlib import Path
from book_angel.cli import main
from book_angel.config import ExamplePair, RulesConfig, save_rules_yaml
from book_angel.exporter import export_book
from book_angel.parser.chunker import chunk_text
from book_angel.parser.epub_engine import parse_epub
from book_angel.staging import StagingWorkspace
from tests.test_epub import create_dummy_epub


def test_full_pipeline_roundtrip(tmp_path: Path):
    # 1. Create dummy epub
    epub_file = tmp_path / "original.epub"
    create_dummy_epub(epub_file, encrypted=False)

    # 2. Ingest
    book = parse_epub(epub_file)
    assert not book.drm_protected

    # 3. Chunk
    chunks = chunk_text(book.chapters[0].content, chapter_title="Chapter 1", chapter_idx=1)

    # 4. Stage
    ws = StagingWorkspace(base_dir=tmp_path, book_slug="full-test")
    ws.initialize(book.title, book.author, book.cover_bytes, RulesConfig(), chunks)

    # 5. Simulate Agent editing a chunk
    chunk_file = ws.chunks_dir / "chunk_001.txt"
    text = chunk_file.read_text(encoding="utf-8")
    edited_text = text.replace("cold and damp", "peaceful and starry")
    chunk_file.write_text(edited_text, encoding="utf-8")

    # 6. Verify Diff
    diffs = ws.get_modified_chunks()
    assert len(diffs) == 1
    assert "peaceful and starry" in diffs[0].modified_text

    # 7. Export
    out_dir = tmp_path / "dist"
    out_epub = export_book(ws, output_dir=out_dir, export_format="epub", title_suffix="[Clean Edition]")

    assert out_epub.exists()
    reparsed = parse_epub(out_epub)
    assert "peaceful and starry" in reparsed.chapters[0].content
    assert reparsed.cover_bytes == b"FAKECONTENTCOVER"


def test_cli_full_workflow_end_to_end(tmp_path: Path, monkeypatch, capsys):
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(tmp_path)

    # 1. Create custom rules in ~/.book-angel/rules.yaml
    custom_rules = RulesConfig(
        romance_level="g-rated",
        violence_level="none",
        language_level="strict_clean",
        custom_rules=["No violence or weapon usage"],
        examples=[ExamplePair(before="he drew his sword", after="he held up a lantern")],
    )
    rules_path = fake_home / ".book-angel" / "rules.yaml"
    save_rules_yaml(custom_rules, rules_path)

    # 2. Create input EPUB
    epub_file = tmp_path / "adventure.epub"
    create_dummy_epub(epub_file, encrypted=False)

    # 3. CLI unpack
    main(["unpack", str(epub_file)])
    captured = capsys.readouterr()
    assert "Successfully unpacked" in captured.out

    staging_dir = tmp_path / ".book-angel" / "staging" / "adventure"
    assert staging_dir.exists()
    rules_md = (staging_dir / "rules.md").read_text(encoding="utf-8")
    assert "Romance Level:** g-rated" in rules_md
    assert "No violence or weapon usage" in rules_md
    assert "he held up a lantern" in rules_md

    # 4. Check CLI status before edits
    main(["status"])
    captured = capsys.readouterr()
    assert "Workspace: adventure | Modified Chunks: 0" in captured.out

    # 5. Agent edits a chunk
    chunks_dir = staging_dir / "chunks"
    chunk_1 = chunks_dir / "chunk_001.txt"
    content = chunk_1.read_text(encoding="utf-8")
    new_content = content.replace("cold and damp", "warm and cozy")
    chunk_1.write_text(new_content, encoding="utf-8")

    # 6. CLI status after edit
    main(["status"])
    captured = capsys.readouterr()
    assert "Workspace: adventure | Modified Chunks: 1" in captured.out

    # 7. CLI review
    main(["review"])
    captured = capsys.readouterr()
    assert "Found 1 modified chunk(s) for review" in captured.out
    assert "+  <p>The night was warm and cozy.</p>" in captured.out
    assert "-  <p>The night was cold and damp.</p>" in captured.out

    # 8. CLI export
    dist_dir = tmp_path / "export_dist"
    main(["export", "--format", "epub", "--out", str(dist_dir), "--suffix", "[Family Edition]"])
    captured = capsys.readouterr()
    assert "Export complete:" in captured.out

    exported_files = list(dist_dir.glob("*.epub"))
    assert len(exported_files) == 1
    reparsed = parse_epub(exported_files[0])
    assert "warm and cozy" in reparsed.chapters[0].content
    assert reparsed.cover_bytes == b"FAKECONTENTCOVER"
