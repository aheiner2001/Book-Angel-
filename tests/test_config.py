from pathlib import Path
from book_angel.config import (
    RulesConfig,
    ExamplePair,
    save_rules_yaml,
    load_rules_yaml,
    generate_rules_markdown,
)


def test_rules_roundtrip_and_markdown(tmp_path: Path):
    cfg = RulesConfig(
        romance_level="mild",
        violence_level="adventure",
        language_level="cleaned",
        omitted_topics=["gay or lesbian themes"],
        custom_rules=["Ensure character humor remains lively."],
        examples=[
            ExamplePair(
                before="He kissed her passionately on the lips, pressing her against the wall.",
                after="He gave her a gentle kiss on the cheek before stepping back.",
            )
        ],
    )

    yaml_file = tmp_path / "rules.yaml"
    save_rules_yaml(cfg, yaml_file)
    assert yaml_file.exists()

    loaded = load_rules_yaml(yaml_file)
    assert loaded.romance_level == "mild"
    assert loaded.violence_level == "adventure"
    assert loaded.language_level == "cleaned"
    assert loaded.omitted_topics == ["gay or lesbian themes"]
    assert loaded.custom_rules == ["Ensure character humor remains lively."]
    assert len(loaded.examples) == 1
    assert loaded.examples[0].before.startswith("He kissed her")
    assert loaded.examples[0].after.startswith("He gave her")

    md_content = generate_rules_markdown(loaded)
    assert "# Book-Angel Content Rules" in md_content
    assert "**Romance Level:** mild" in md_content
    assert "**Violence Level:** adventure" in md_content
    assert "**Language Level:** cleaned" in md_content
    assert "## Omitted Topics / Themes" in md_content
    assert "- Do not include: gay or lesbian themes" in md_content
    assert "## Custom Rules" in md_content
    assert "- Ensure character humor remains lively." in md_content
    assert "### Few-Shot Editing Examples" in md_content
    assert "Original:" in md_content
    assert "Revised:" in md_content


def test_load_nonexistent_yaml_returns_defaults(tmp_path: Path):
    missing_file = tmp_path / "nonexistent.yaml"
    cfg = load_rules_yaml(missing_file)
    assert cfg.romance_level == "mild"
    assert cfg.violence_level == "adventure"
    assert cfg.language_level == "cleaned"
    assert cfg.omitted_topics == []
    assert cfg.custom_rules == []
    assert cfg.examples == []


def test_save_and_load_with_string_path(tmp_path: Path):
    yaml_path_str = str(tmp_path / "rules_str.yaml")
    cfg = RulesConfig(romance_level="none", custom_rules=["Keep names unchanged."])
    save_rules_yaml(cfg, yaml_path_str)

    loaded = load_rules_yaml(yaml_path_str)
    assert loaded.romance_level == "none"
    assert loaded.custom_rules == ["Keep names unchanged."]


def test_generate_markdown_with_defaults():
    cfg = RulesConfig()
    md_content = generate_rules_markdown(cfg)
    assert "# Book-Angel Content Rules" in md_content
    assert "**Romance Level:** mild" in md_content
    assert "**Violence Level:** adventure" in md_content
    assert "**Language Level:** cleaned" in md_content
    assert "## Omitted Topics / Themes" not in md_content
    assert "## Custom Rules" not in md_content
    assert "### Few-Shot Editing Examples" not in md_content


def test_character_mapping_roundtrip_and_markdown(tmp_path: Path):
    from book_angel.config import CharacterMapping
    cfg = RulesConfig(
        character_mappings=[
            CharacterMapping(
                original_name="Julian",
                new_name="Julia",
                new_gender="female",
                pronouns="she/her/hers",
                instruction="Transform Julian into Julia naturally.",
            )
        ]
    )
    yaml_file = tmp_path / "rules_cm.yaml"
    save_rules_yaml(cfg, yaml_file)
    assert yaml_file.exists()

    loaded = load_rules_yaml(yaml_file)
    assert len(loaded.character_mappings) == 1
    assert loaded.character_mappings[0].original_name == "Julian"
    assert loaded.character_mappings[0].new_name == "Julia"
    assert loaded.character_mappings[0].pronouns == "she/her/hers"

    md = generate_rules_markdown(loaded)
    assert "## Character & Gender Transformations" in md
    assert "Transform Character 'Julian'** -> **'Julia'" in md
    assert "Target Pronouns: she/her/hers" in md
