from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class Rule:
    name: str
    action: str
    message: str
    pattern: Optional[str] = None
    type: Optional[str] = None
    min_digits: int = 13
    max_digits: int = 19


@dataclass
class FilterConfig:
    rules: list[Rule] = field(default_factory=list)
    allowed_file_types: list[str] = field(default_factory=list)


def load_rules(path: str) -> FilterConfig:
    with open(path) as f:
        data = yaml.safe_load(f)

    rules = []
    for r in data.get("rules", []):
        rules.append(Rule(
            name=r["name"],
            action=r["action"],
            message=r["message"],
            pattern=r.get("pattern"),
            type=r.get("type"),
            min_digits=r.get("min_digits", 13),
            max_digits=r.get("max_digits", 19),
        ))

    return FilterConfig(
        rules=rules,
        allowed_file_types=data.get("allowed_file_types", []),
    )
