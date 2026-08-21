"""Unit tests for the pure-Python helpers in src/silver/comment_apply.py."""

from comment_apply import _escape_comment, generate_comment_sql


def test_escape_comment_doubles_single_quotes():
    assert _escape_comment("it's a test") == "it''s a test"


def test_escape_comment_leaves_plain_text_untouched():
    assert _escape_comment("plain comment") == "plain comment"


def test_generate_comment_sql_emits_table_and_column_statements():
    metadata = {
        "issue": {
            "comment": "Canonical issue entity",
            "columns": {"id": "Issue id", "summary": "Short summary"},
        }
    }

    stmts = generate_comment_sql("cat", "silver", metadata)

    assert (
        "COMMENT ON TABLE `cat`.`silver`.`issue` IS 'Canonical issue entity';"
        in stmts
    )
    assert (
        "COMMENT ON COLUMN `cat`.`silver`.`issue`.`id` IS 'Issue id';" in stmts
    )
    assert len(stmts) == 3


def test_generate_comment_sql_escapes_quotes_in_comments():
    metadata = {"t": {"comment": "user's table"}}

    stmts = generate_comment_sql("c", "s", metadata)

    assert stmts == ["COMMENT ON TABLE `c`.`s`.`t` IS 'user''s table';"]


def test_generate_comment_sql_skips_non_dict_columns():
    metadata = {"t": {"comment": "c", "columns": "not-a-dict"}}

    stmts = generate_comment_sql("c", "s", metadata)

    # Only the table comment survives; malformed columns are ignored, not raised.
    assert stmts == ["COMMENT ON TABLE `c`.`s`.`t` IS 'c';"]


def test_generate_comment_sql_omits_table_comment_when_absent():
    metadata = {"t": {"columns": {"a": "col a"}}}

    stmts = generate_comment_sql("c", "s", metadata)

    assert stmts == ["COMMENT ON COLUMN `c`.`s`.`t`.`a` IS 'col a';"]
