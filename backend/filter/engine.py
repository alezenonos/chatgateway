from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional
from filter.rules import load_rules, FilterConfig
from filter.luhn import find_card_numbers


@dataclass
class FilterResult:
    blocked: bool = False
    warned: bool = False
    rule: Optional[str] = None
    message: Optional[str] = None


class ContentFilter:
    def __init__(self, config_path: str):
        self.config: FilterConfig = load_rules(config_path)

    def scan_text(self, text: str) -> FilterResult:
        for rule in self.config.rules:
            if rule.type == "luhn":
                matches = find_card_numbers(text, rule.min_digits, rule.max_digits)
                if matches:
                    if rule.action == "block":
                        return FilterResult(blocked=True, rule=rule.name, message=rule.message)
                    else:
                        return FilterResult(warned=True, rule=rule.name, message=rule.message)
            elif rule.pattern:
                if re.search(rule.pattern, text):
                    if rule.action == "block":
                        return FilterResult(blocked=True, rule=rule.name, message=rule.message)
                    else:
                        return FilterResult(warned=True, rule=rule.name, message=rule.message)

        return FilterResult()

    def is_file_type_allowed(self, extension: str) -> bool:
        return extension.lower() in self.config.allowed_file_types
