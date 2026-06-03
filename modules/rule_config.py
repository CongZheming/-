from __future__ import annotations

import ast
from functools import lru_cache
from typing import Any

from modules.utils import PROJECT_ROOT

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised only when PyYAML is unavailable
    yaml = None


CONFIG_DIR = PROJECT_ROOT / "config"
LABELS_PATH = CONFIG_DIR / "labels.yaml"
RULES_PATH = CONFIG_DIR / "rules.yaml"


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") or value.startswith(("'", '"')):
        return ast.literal_eval(value)
    try:
        return int(value)
    except ValueError:
        return value


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return {}, index

        if _line_indent(lines[index]) == indent and lines[index].lstrip().startswith("- "):
            values = []
            while index < len(lines) and _line_indent(lines[index]) == indent and lines[index].lstrip().startswith("- "):
                values.append(_parse_scalar(lines[index].lstrip()[2:]))
                index += 1
            return values, index

        values: dict[str, Any] = {}
        while index < len(lines):
            line = lines[index]
            current_indent = _line_indent(line)
            if current_indent < indent:
                break
            if current_indent != indent:
                break

            key, separator, raw_value = line.strip().partition(":")
            if not separator:
                raise ValueError(f"Invalid config line: {line}")

            raw_value = raw_value.strip()
            if raw_value:
                values[key] = _parse_scalar(raw_value)
                index += 1
                continue

            child_indent = _line_indent(lines[index + 1]) if index + 1 < len(lines) else indent + 2
            child, index = parse_block(index + 1, child_indent)
            values[key] = child

        return values, index

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        raise ValueError("Classifier config root must be a mapping")
    return parsed


def _read_yaml(path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing classifier config: {path}")
    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text) if yaml else _parse_simple_yaml(raw_text)
    if not isinstance(data, dict):
        raise ValueError(f"Classifier config must be a mapping: {path}")
    return data


@lru_cache(maxsize=1)
def load_label_options() -> dict[str, list[str]]:
    data = _read_yaml(LABELS_PATH)
    return {str(label_type): [str(label) for label in labels or []] for label_type, labels in data.items()}


@lru_cache(maxsize=1)
def load_rule_config() -> dict[str, Any]:
    return _read_yaml(RULES_PATH)
