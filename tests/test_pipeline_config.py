"""Unit tests for the config parsing in scripts/read_pipeline_config.py."""

from read_pipeline_config import _parse_flat_yaml, pipeline_config


def test_parse_flat_yaml_reads_quoted_and_unquoted_values():
    text = '\n'.join(
        [
            "# a comment",
            'catalog: "my_catalog"',
            "silver_schema: jira_silver",
            "owner_email: 'user@example.com'",
            "",
            "   ",
        ]
    )

    cfg = _parse_flat_yaml(text)

    assert cfg["catalog"] == "my_catalog"
    assert cfg["silver_schema"] == "jira_silver"
    assert cfg["owner_email"] == "user@example.com"


def test_parse_flat_yaml_ignores_comments_and_blank_lines():
    cfg = _parse_flat_yaml("# only a comment\n\n")
    assert cfg == {}


def test_pipeline_config_overrides_propagate_catalog_to_layers():
    cfg = pipeline_config(overrides={"catalog": "override_cat"})

    assert cfg["catalog"] == "override_cat"
    for layer in ("bronze", "silver", "gold", "metrics"):
        assert cfg[f"{layer}_catalog"] == "override_cat"


def test_pipeline_config_explicit_layer_catalog_wins_over_derived():
    cfg = pipeline_config(
        overrides={"catalog": "cat", "gold_catalog": "special_gold"}
    )

    assert cfg["gold_catalog"] == "special_gold"
    assert cfg["silver_catalog"] == "cat"


def test_pipeline_config_supplies_default_schema_names():
    cfg = pipeline_config()

    assert cfg["bronze_schema"]
    assert cfg["silver_schema"]
    assert cfg["gold_schema"]
    assert cfg["metrics_schema"]
