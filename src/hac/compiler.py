"""Controlled-natural-language front end for common contract patterns."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .formal import formula
from .model import Rule


@dataclass(frozen=True, slots=True)
class CompiledRequirement:
    source: str
    rule: Rule

    @property
    def formula(self) -> str:
        return formula(self.rule)


class RequirementCompiler:
    """Compile deliberately constrained English into deterministic rules.

    This is not a claim of correct arbitrary-NL translation. Unsupported or
    ambiguous text fails closed and must be clarified by a human.
    """

    _patterns = (
        (
            re.compile(r"^never\s+(.+?)[.]?$", re.I),
            lambda m: ("forbid", {"action": _slug(m.group(1))}),
        ),
        (
            re.compile(r"^require\s+(.+?)\s+before\s+(.+?)[.]?$", re.I),
            lambda m: (
                "requires_before",
                {"required": _slug(m.group(1)), "action": _slug(m.group(2))},
            ),
        ),
        (
            re.compile(
                r"^after\s+(.+?),?\s+require\s+(.+?)\s+within\s+([0-9.]+)\s*"
                r"(seconds?|minutes?|hours?)[.]?$",
                re.I,
            ),
            lambda m: (
                "response_within",
                {
                    "trigger": _slug(m.group(1)),
                    "response": _slug(m.group(2)),
                    "within_seconds": float(m.group(3)) * _unit(m.group(4)),
                },
            ),
        ),
        (
            re.compile(
                r"^keep\s+([a-zA-Z][\w ]*)\s*(<=|>=|<|>)\s*"
                r"([0-9]+(?:\.[0-9]+)?)[.]?$",
                re.I,
            ),
            lambda m: (
                "field_limit",
                {"field": _slug(m.group(1)), "op": m.group(2), "value": float(m.group(3))},
            ),
        ),
        (
            re.compile(r"^limit\s+(.+?)\s+to\s+([0-9]+)\s+times?[.]?$", re.I),
            lambda m: ("count_limit", {"action": _slug(m.group(1)), "max": int(m.group(2))}),
        ),
    )

    def compile(self, text: str, *, rule_id: str = "compiled.requirement") -> CompiledRequirement:
        source = " ".join(text.strip().split())
        for pattern, builder in self._patterns:
            match = pattern.fullmatch(source)
            if match:
                kind, params = builder(match)
                return CompiledRequirement(
                    source=source,
                    rule=Rule(
                        id=rule_id,
                        kind=kind,
                        description=source.rstrip("."),
                        params=params,
                        source="controlled-natural-language",
                    ),
                )
        raise ValueError(
            "ambiguous or unsupported requirement; use one of: Never X; "
            "Require X before Y; After X require Y within N seconds; "
            "Keep FIELD <= N; Limit X to N times"
        )


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return value.strip("_")


def _unit(value: str) -> float:
    unit = value.lower()
    if unit.startswith("second"):
        return 1.0
    if unit.startswith("minute"):
        return 60.0
    return 3600.0
