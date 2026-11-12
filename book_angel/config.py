"""Configuration and rules engine for Book-Angel."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import yaml


@dataclass
class ExamplePair:
    before: str
    after: str


@dataclass
class RulesConfig:
    romance_level: str = "mild"
    violence_level: str = "adventure"
    language_level: str = "cleaned"
    omitted_topics: list[str] = field(default_factory=list)
    custom_rules: list[str] = field(default_factory=list)
    examples: list[ExamplePair] = field(default_factory=list)


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
        data = yaml.safe_load(f) or {}

    examples = [
        ExamplePair(before=ex["before"], after=ex["after"])
        for ex in data.get("examples", [])
        if isinstance(ex, dict) and "before" in ex and "after" in ex
    ]
    return RulesConfig(
        romance_level=data.get("romance_level", "mild"),
        violence_level=data.get("violence_level", "adventure"),
        language_level=data.get("language_level", "cleaned"),
        omitted_topics=data.get("omitted_topics", []),
        custom_rules=data.get("custom_rules", []),
        examples=examples,
    )


def generate_rules_markdown(config: RulesConfig) -> str:
    """Generate Markdown instructions for editor agents from RulesConfig."""
    lines = [
        "# Book-Angel Content Rules",
        "",
        "You are acting as an editorial assistant following strict narrative filtering guidelines.",
        "Modify only passages that conflict with these rules. Keep all other prose, tone, and character voices intact.",
        "",
        "## Policy Levels",
        f"- **Romance Level:** {config.romance_level}",
        f"- **Violence Level:** {config.violence_level}",
        f"- **Language Level:** {config.language_level}",
        "",
    ]

    if config.omitted_topics:
        lines.append("## Omitted Topics / Themes")
        for topic in config.omitted_topics:
            lines.append(f"- Do not include: {topic}")
        lines.append("")

    if config.custom_rules:
        lines.append("## Custom Rules")
        for rule in config.custom_rules:
            lines.append(f"- {rule}")
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
