from filter.luhn import is_luhn_valid, find_card_numbers


def test_valid_card_number():
    assert is_luhn_valid("4111111111111111") is True


def test_invalid_card_number():
    assert is_luhn_valid("4111111111111112") is False


def test_find_card_in_text():
    text = "My card is 4111111111111111 please charge it"
    results = find_card_numbers(text)
    assert len(results) == 1
    assert results[0] == "4111111111111111"


def test_no_card_in_text():
    text = "This is a normal message about quarterly revenue of 1234567890123"
    results = find_card_numbers(text)
    assert len(results) == 0


def test_multiple_cards():
    text = "Cards: 4111111111111111 and 5500000000000004"
    results = find_card_numbers(text)
    assert len(results) == 2
