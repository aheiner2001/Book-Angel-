"""Command line interface for Book-Angel."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from book_angel import __version__
from book_angel.config import RulesConfig, load_rules_yaml, save_rules_yaml
from book_angel.exporter import export_book
from book_angel.parser.chunker import chunk_text
from book_angel.parser.epub_engine import parse_epub
from book_angel.parser.pdf_engine import parse_pdf
from book_angel.staging import StagingWorkspace, generate_unified_diff


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the Book-Angel command-line parser."""
    parser = argparse.ArgumentParser(
        prog="book-angel",
        description="Book-Angel: AI-assisted book content transformation and filtering.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # config
    subparsers.add_parser("config", help="Launch interactive rules configuration wizard.")

    # unpack
    p_unpack = subparsers.add_parser("unpack", help="Unpack EPUB or PDF into staging chunks.")
    p_unpack.add_argument("file", type=str, help="Path to EPUB or PDF book.")

    # review
    subparsers.add_parser("review", help="Review modified chunks interactively.")

    # export
    p_export = subparsers.add_parser("export", help="Reassemble approved chunks into book.")
    p_export.add_argument(
        "--format",
        choices=["epub", "pdf"],
        default="epub",
        help="Target output format.",
    )
    p_export.add_argument("--suffix", type=str, default="[Clean Edition]", help="Title suffix.")
    p_export.add_argument("--out", type=str, default="dist", help="Output directory.")

    # status
    subparsers.add_parser("status", help="Show status of current staging workspace.")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Execute the Book-Angel CLI application."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "config":
        print("=== Book-Angel Configuration Wizard ===")
        print("Setting up rules in ~/.book-angel/rules.yaml...")
        config_path = Path.home() / ".book-angel" / "rules.yaml"
        current = load_rules_yaml(config_path)
        save_rules_yaml(current, config_path)
        print(f"Rules saved to {config_path}")

    elif args.command == "unpack":
        book_path = Path(args.file)
        if not book_path.exists():
            print(f"Error: File not found: {book_path}", file=sys.stderr)
            sys.exit(1)

        slug = book_path.stem.lower().replace(" ", "-")
        ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slug)

        rules_path = Path.home() / ".book-angel" / "rules.yaml"
        rules_cfg = load_rules_yaml(rules_path) if rules_path.exists() else RulesConfig()

        if book_path.suffix.lower() == ".epub":
            with parse_epub(book_path) as epub:
                if epub.drm_protected:
                    print(
                        f"Error: {book_path.name} is DRM-protected. Please remove DRM before processing.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                chunks = []
                chunk_id = 1
                for idx, ch in enumerate(epub.chapters, 1):
                    c = chunk_text(
                        ch.content,
                        chapter_title=ch.title,
                        chapter_idx=idx,
                        start_chunk_id=chunk_id,
                    )
                    chunks.extend(c)
                    chunk_id += len(c)
                ws.initialize(epub.title, epub.author, epub.cover_bytes, rules_cfg, chunks)
                print(f"Successfully unpacked {len(chunks)} chunks into {ws.chunks_dir}")

        elif book_path.suffix.lower() == ".pdf":
            pdf = parse_pdf(book_path)
            if pdf.is_scanned_or_empty:
                print(f"Error: No text found in {book_path.name}. OCR required.", file=sys.stderr)
                sys.exit(1)
            joined = "\n\n".join(pdf.pages)
            chunks = chunk_text(joined, chapter_title=pdf.title, chapter_idx=1)
            ws.initialize(pdf.title, pdf.author, None, rules_cfg, chunks)
            print(f"Successfully unpacked {len(chunks)} chunks into {ws.chunks_dir}")
        else:
            print(
                f"Error: Unsupported file format '{book_path.suffix}'. Expected .epub or .pdf",
                file=sys.stderr,
            )
            sys.exit(1)

    elif args.command == "review":
        staging_root = Path.cwd() / ".book-angel" / "staging"
        slugs = sorted([d.name for d in staging_root.iterdir() if d.is_dir()]) if staging_root.exists() else []
        if not slugs:
            print("No active book staging found.")
            return
        ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slugs[0])
        diffs = ws.get_modified_chunks()
        if not diffs:
            print("No modified chunks to review. All chunks match original.")
            return
        print(f"Found {len(diffs)} modified chunk(s) for review:\n")
        for diff in diffs:
            print(f"--- Chunk {diff.chunk_id:03d} ---")
            print(generate_unified_diff(diff))

    elif args.command == "export":
        staging_root = Path.cwd() / ".book-angel" / "staging"
        slugs = sorted([d.name for d in staging_root.iterdir() if d.is_dir()]) if staging_root.exists() else []
        if not slugs:
            print("No active book staging found.", file=sys.stderr)
            sys.exit(1)
        ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slugs[0])
        out_file = export_book(
            ws,
            Path(args.out),
            export_format=args.format,
            title_suffix=args.suffix,
        )
        print(f"Export complete: {out_file}")

    elif args.command == "status":
        staging_root = Path.cwd() / ".book-angel" / "staging"
        if not staging_root.exists():
            print("No active staging workspaces.")
            return
        found = False
        for slug_dir in sorted(staging_root.iterdir()):
            if slug_dir.is_dir():
                found = True
                ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slug_dir.name)
                diffs = ws.get_modified_chunks()
                print(f"Workspace: {slug_dir.name} | Modified Chunks: {len(diffs)}")
        if not found:
            print("No active staging workspaces.")


if __name__ == "__main__":
    main()
