import os
from filter.rules import load_rules
from filter.engine import ContentFilter, FilterResult


FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "content-filter.yaml")


def test_load_rules_from_yaml():
    rules = load_rules(FIXTURE_PATH)
    assert len(rules.rules) >= 4
    assert rules.allowed_file_types == [".csv", ".xlsx", ".pdf", ".txt", ".png", ".jpg"]


def test_filter_blocks_ni_number():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("My NI number is AB123456C")
    assert result.blocked is True
    assert result.rule == "uk_national_insurance"


def test_filter_blocks_credit_card():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Pay with 4111111111111111 please")
    assert result.blocked is True
    assert result.rule == "credit_card"


def test_filter_blocks_bank_account():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Bank details: 12-34-56 12345678")
    assert result.blocked is True
    assert result.rule == "uk_bank_account"


def test_filter_warns_email():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Contact john@example.com for details")
    assert result.blocked is False
    assert result.warned is True
    assert result.rule == "email_address"


def test_filter_passes_clean_text():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("What is the quarterly revenue trend?")
    assert result.blocked is False
    assert result.warned is False


def test_filter_checks_file_type_allowed():
    f = ContentFilter(FIXTURE_PATH)
    assert f.is_file_type_allowed(".csv") is True
    assert f.is_file_type_allowed(".exe") is False


# --- Regression tests: edge cases ---

def test_filter_ni_number_lowercase_does_not_match():
    """NI numbers must be uppercase — lowercase should pass through."""
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("reference ab123456c")
    assert result.blocked is False


def test_filter_ni_number_embedded_in_text():
    """NI number inside a sentence should still be caught."""
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Employee NI:AB123456C is on file")
    assert result.blocked is True


def test_filter_multiple_rules_first_match_wins():
    """If text matches multiple rules, the first rule in YAML order blocks."""
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("NI AB123456C and card 4111111111111111")
    assert result.blocked is True
    assert result.rule == "uk_national_insurance"


def test_filter_clean_financial_figures():
    """Normal financial numbers should not trigger card detection."""
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Revenue was 1500000 with expenses of 890000")
    assert result.blocked is False


def test_filter_file_type_case_insensitive():
    """File extension check should be case insensitive."""
    f = ContentFilter(FIXTURE_PATH)
    assert f.is_file_type_allowed(".CSV") is True
    assert f.is_file_type_allowed(".Xlsx") is True
    assert f.is_file_type_allowed(".EXE") is False


def test_filter_empty_text():
    """Empty string should pass without error."""
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("")
    assert result.blocked is False
    assert result.warned is False


def test_filter_long_text_with_ni_at_end():
    """Sensitive data at the end of a long message should still be caught."""
    f = ContentFilter(FIXTURE_PATH)
    long_text = "This is a very long message about quarterly results. " * 50
    long_text += "By the way my NI is AB123456C"
    result = f.scan_text(long_text)
    assert result.blocked is True
