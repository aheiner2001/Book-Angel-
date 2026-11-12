"""Configuration and rules engine for Book-Angel."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
import subprocess
import yaml


@dataclass
class ExamplePair:
    before: str
    after: str


@dataclass
class CharacterMapping:
    original_name: str
    new_name: str
    new_gender: str = "female"
    pronouns: str = "she/her/hers"
    instruction: str = ""


@dataclass
class RulesConfig:
    romance_level: str = "mild"
    violence_level: str = "adventure"
    language_level: str = "cleaned"
    omitted_topics: list[str] = field(default_factory=list)
    custom_rules: list[str] = field(default_factory=list)
    examples: list[ExamplePair] = field(default_factory=list)
    character_mappings: list[CharacterMapping] = field(default_factory=list)


def get_default_rules_path() -> Path:
    """Get the default global rules.yaml path in user config dir."""
    return Path.home() / ".book-angel" / "rules.yaml"


def get_project_rules_path() -> Path:
    """Get the active rules path, preferring local rules.yaml if present."""
    local = Path.cwd() / "rules.yaml"
    if local.exists():
        return local
    return get_default_rules_path()


def get_plain_text_rules_path() -> Path:
    """Get the path to rules.txt, checking local directory first."""
    local_txt = Path.cwd() / "rules.txt"
    if local_txt.exists():
        return local_txt
    user_txt = Path.home() / ".book-angel" / "rules.txt"
    if user_txt.exists():
        return user_txt
    return local_txt


def load_plain_text_rules(path: Path | str | None = None) -> str | None:
    """Read plain text rules if rules.txt exists and is not empty."""
    p = Path(path) if path else get_plain_text_rules_path()
    if p.exists():
        content = p.read_text(encoding="utf-8").strip()
        if content:
            return content
    return None


def open_file_in_editor(path: Path | str) -> None:
    """Open a file in the user's default system editor (Cursor, VS Code, or TextEdit)."""
    p = Path(path)
    if os.uname().sysname == "Darwin":
        subprocess.run(["open", str(p)], check=False)
    else:
        try:
            os.startfile(str(p))  # type: ignore[attr-defined]
        except AttributeError:
            subprocess.run(["xdg-open", str(p)], check=False)


def save_rules_yaml(config: RulesConfig, path: Path | str) -> None:
    """Serialize a RulesConfig object to a YAML file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    raw_dict = asdict(config)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(raw_dict, f, sort_keys=False)


def load_rules_yaml(path: Path | str) -> RulesConfig:
    """Load and parse a RulesConfig from a YAML file. Returns default if not found."""
    p = Path(path)
    if not p.exists():
        return RulesConfig()
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return RulesConfig()

    examples = [
        ExamplePair(before=ex["before"], after=ex["after"])
        for ex in data.get("examples", [])
        if isinstance(ex, dict) and "before" in ex and "after" in ex
    ]
    character_mappings = [
        CharacterMapping(
            original_name=cm.get("original_name", ""),
            new_name=cm.get("new_name", ""),
            new_gender=cm.get("new_gender", "female"),
            pronouns=cm.get("pronouns", "she/her/hers"),
            instruction=cm.get("instruction", ""),
        )
        for cm in data.get("character_mappings", [])
        if isinstance(cm, dict) and cm.get("original_name") and cm.get("new_name")
    ]
    return RulesConfig(
        romance_level=data.get("romance_level", "mild"),
        violence_level=data.get("violence_level", "adventure"),
        language_level=data.get("language_level", "cleaned"),
        omitted_topics=data.get("omitted_topics", []),
        custom_rules=data.get("custom_rules", []),
        examples=examples,
        character_mappings=character_mappings,
    )


def generate_rules_markdown(config: RulesConfig, raw_text: str | None = None) -> str:
    """Generate Markdown instructions for editor agents from RulesConfig and optional raw text."""
    lines = [
        "# Book-Angel Content Rules",
        "",
        "> **CRITICAL SURGICAL EDITING DIRECTIVE:**",
        "> - You are an editor with a scalpel, NOT a general re-writer.",
        "> - Do NOT rewrite paragraphs for style, vocabulary, or flow.",
        "> - Only modify the exact sentences that directly conflict with the user's specific rules below.",
        "> - Leave 99% of the prose completely untouched and 100% bit-for-bit identical to the author's original words.",
        "> - If a sentence or paragraph does not violate any rule, do NOT touch a single word.",
        "",
    ]

    plain_rules = raw_text if raw_text is not None else load_plain_text_rules()
    if plain_rules:
        lines.append("## Plain-English User Rules (from rules.txt)")
        lines.append("Follow these exact instructions provided directly by the user:")
        lines.append("")
        lines.append(plain_rules)
        lines.append("")

    if config.custom_rules:
        lines.append("## Custom Rules")
        lines.append("When you encounter these specific situations in the book, apply these exact instructions:")
        lines.append("")
        for rule in config.custom_rules:
            lines.append(f"- {rule}")
        lines.append("")

    if config.character_mappings:
        lines.append("## Character & Gender Transformations")
        lines.append(
            "Adapt the specified characters so all relationships, dialogue, and narrative interactions remain natural:"
        )
        lines.append("")
        for cm in config.character_mappings:
            lines.append(f"- **Transform Character '{cm.original_name}'** -> **'{cm.new_name}'**")
            lines.append(f"  - Target Gender: {cm.new_gender}")
            lines.append(f"  - Target Pronouns: {cm.pronouns}")
            if cm.instruction:
                lines.append(f"  - Guidance: {cm.instruction}")
            else:
                lines.append(
                    f"  - Guidance: Replace all occurrences of '{cm.original_name}' with '{cm.new_name}', updating all associated pronouns and physical/gender descriptors naturally."
                )
        lines.append("")

    lines.append("## Policy Levels")
    lines.append(f"- **Romance Level:** {config.romance_level}")
    lines.append(f"- **Violence Level:** {config.violence_level}")
    lines.append(f"- **Language Level:** {config.language_level}")
    lines.append("")

    if config.omitted_topics:
        lines.append("## Omitted Topics / Themes")
        for topic in config.omitted_topics:
            lines.append(f"- Do not include: {topic}")
        lines.append("")

    if config.examples:
        lines.append("### Few-Shot Editing Examples")
        lines.append("Follow these patterns for tone and replacement style:")
        lines.append("")
        for idx, ex in enumerate(config.examples, 1):
            lines.append(f"**Example {idx}:**")
            lines.append(f"> **Original:** {ex.before}")
            lines.append(f"> **Revised:** {ex.after}")
            lines.append("")

    return "\n".join(lines)
