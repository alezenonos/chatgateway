import re


def is_luhn_valid(number_str: str) -> bool:
    digits = [int(d) for d in number_str]
    digits.reverse()
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_card_numbers(text: str, min_digits: int = 13, max_digits: int = 19) -> list[str]:
    pattern = rf'\b(\d{{{min_digits},{max_digits}}})\b'
    candidates = re.findall(pattern, text)
    return [c for c in candidates if is_luhn_valid(c)]
