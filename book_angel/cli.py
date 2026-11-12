"""Command line interface for Book-Angel."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from book_angel import __version__
from book_angel.config import (
    CharacterMapping,
    RulesConfig,
    get_default_rules_path,
    load_rules_yaml,
    open_file_in_editor,
    save_rules_yaml,
)
from book_angel.exporter import export_book
from book_angel.parser.chunker import chunk_text
from book_angel.parser.epub_engine import parse_epub
from book_angel.parser.pdf_engine import parse_pdf
from book_angel.staging import StagingWorkspace, generate_unified_diff


def prompt_mac_file_picker() -> Path | None:
    """Prompt the user to select an EPUB or PDF using the native macOS Finder dialog."""
    if sys.platform != "darwin":
        return None
    try:
        script = 'POSIX path of (choose file with prompt "Select your EPUB or PDF book:" of type {"epub", "pdf"})'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except Exception:
        pass
    return None


def get_default_export_dir() -> Path:
    """Get the default export directory, prioritizing user's Downloads folder."""
    downloads = Path.home() / "Downloads"
    if downloads.exists() and downloads.is_dir():
        return downloads
    return Path("dist")


def run_interactive_config(rules_path: Path) -> None:
    """Guide the user through an interactive configuration walkthrough."""
    print("\n=== ⚙️  Book-Angel Rules Configuration ===")
    current = load_rules_yaml(rules_path)

    print(f"Active Rules File: {rules_path}")
    print(f"1. Romance Level (Current: {current.romance_level})")
    print("   [1] Mild (clean kissing, fade-to-black on intimacy - Recommended)")
    print("   [2] Clean (no kissing or romance)")
    print("   [3] Moderate (romantic themes intact, soft fade)")
    r_choice = input("Select romance level [press Enter to keep current]: ").strip()
    if r_choice == "1":
        current.romance_level = "mild"
    elif r_choice == "2":
        current.romance_level = "clean"
    elif r_choice == "3":
        current.romance_level = "moderate"

    print(f"\n2. Violence Level (Current: {current.violence_level})")
    print("   [1] Adventure (action intact, reduce graphic gore/viscera - Recommended)")
    print("   [2] Mild / Minimal")
    v_choice = input("Select violence level [press Enter to keep current]: ").strip()
    if v_choice == "1":
        current.violence_level = "adventure"
    elif v_choice == "2":
        current.violence_level = "mild"

    print("\n3. Character & Gender Transformations")
    if current.character_mappings:
        print("Current transformations:")
        for cm in current.character_mappings:
            print(f"   - {cm.original_name} -> {cm.new_name} ({cm.pronouns})")
    add_cm = input("Would you like to add a character transformation rule? [y/N]: ").strip().lower()
    if add_cm == "y":
        orig = input("   Original character name in book: ").strip()
        new_n = input("   New character name: ").strip()
        new_g = input("   New gender (e.g. female / male) [default: female]: ").strip() or "female"
        pron = input("   Target pronouns (e.g. she/her/hers) [default: she/her/hers]: ").strip() or "she/her/hers"
        inst = input("   Any custom notes (optional): ").strip()
        if orig and new_n:
            current.character_mappings.append(
                CharacterMapping(
                    original_name=orig,
                    new_name=new_n,
                    new_gender=new_g,
                    pronouns=pron,
                    instruction=inst,
                )
            )
            print(f"   ✅ Added rule: {orig} -> {new_n} ({pron})")

    save_rules_yaml(current, rules_path)
    print(f"\n✅ Rules saved to: {rules_path}")
    open_now = input("Would you like to open rules.yaml in your text editor to view/edit? [Y/n]: ").strip().lower()
    if open_now != "n":
        open_file_in_editor(rules_path)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the Book-Angel command-line parser."""
    parser = argparse.ArgumentParser(
        prog="book-angel",
        description="Book-Angel: AI-assisted book content transformation and filtering.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=False)

    # config
    p_config = subparsers.add_parser("config", help="Launch interactive rules configuration wizard.")
    p_config.add_argument("--open", action="store_true", help="Open rules.yaml in default editor.")

    # unpack
    p_unpack = subparsers.add_parser("unpack", help="Unpack EPUB or PDF into staging chunks.")
    p_unpack.add_argument("file", nargs="?", default=None, help="Path to EPUB or PDF book (omit to open Finder).")

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
    p_export.add_argument(
        "--out",
        type=str,
        default=str(get_default_export_dir()),
        help=f"Output directory (default: {get_default_export_dir()}).",
    )

    # status
    subparsers.add_parser("status", help="Show status of current staging workspace.")

    return parser


def run_interactive_menu() -> None:
    """Display the interactive launcher menu when run without subcommands."""
    rules_path = get_default_rules_path()
    if not rules_path.exists():
        save_rules_yaml(RulesConfig(), rules_path)
    rules_cfg = load_rules_yaml(rules_path)

    print("\n" + "=" * 60)
    print("              📖  Welcome to Book-Angel")
    print("=" * 60)
    print(f"Active Rules File: {rules_path}")
    print(f"  • Romance Level:    {rules_cfg.romance_level}")
    print(f"  • Violence Level:   {rules_cfg.violence_level}")
    print(f"  • Character Rules:  {len(rules_cfg.character_mappings)} configured")
    print(f"  • Export Directory: {get_default_export_dir()}")
    print("-" * 60)
    print("[1] 📂 Open a Book (Opens Mac Finder dialog to select EPUB/PDF)")
    print("[2] ⚙️  Configure Rules & Character Transformations")
    print("[3] 📝 Open rules.yaml in Text Editor / Cursor")
    print("[4] 🔍 Review Chunk Diffs")
    print("[5] 📦 Export Clean Book to Downloads")
    print("[Q] ❌ Quit")
    print("=" * 60)

    try:
        choice = input("Choose an option [1-5, Q]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "1":
        main(["unpack"])
    elif choice == "2":
        main(["config"])
    elif choice == "3":
        open_file_in_editor(rules_path)
        print(f"Opened {rules_path} in your editor.")
    elif choice == "4":
        main(["review"])
    elif choice == "5":
        main(["export"])
    elif choice in ("q", "quit", "exit"):
        print("Goodbye!")
        sys.exit(0)


def main(argv: list[str] | None = None) -> None:
    """Execute the Book-Angel CLI application."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        run_interactive_menu()
        return

    rules_path = get_default_rules_path()

    if args.command == "config":
        print("=== Book-Angel Configuration Wizard ===")
        print(f"Setting up rules in {rules_path}...")
        if getattr(args, "open", False):
            if not rules_path.exists():
                save_rules_yaml(RulesConfig(), rules_path)
            open_file_in_editor(rules_path)
            print(f"Opened {rules_path} in default editor.")
            return

        current = load_rules_yaml(rules_path)
        save_rules_yaml(current, rules_path)
        print(f"Rules saved to {rules_path}")

        if sys.stdin.isatty():
            run_interactive_config(rules_path)

    elif args.command == "unpack":
        book_file_str = args.file
        if not book_file_str:
            print("Opening macOS Finder to select your book...")
            picked = prompt_mac_file_picker()
            if not picked:
                print("No file selected.", file=sys.stderr)
                return
            book_path = picked
        else:
            book_path = Path(book_file_str)

        if not book_path.exists():
            print(f"Error: File not found: {book_path}", file=sys.stderr)
            sys.exit(1)

        slug = book_path.stem.lower().replace(" ", "-")
        ws = StagingWorkspace(base_dir=Path.cwd(), book_slug=slug)

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
                print(f"Rules applied from: {rules_path}")

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
