"""Immutable data model and JSON loaders for HAC contracts."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping


SUPPORTED_RULES = {
    "forbid",
    "requires_before",
    "response_within",
    "field_limit",
    "cumulative_limit",
    "count_limit",
}


def _frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True)
class Rule:
    """A reviewable requirement with deterministic monitor semantics."""

    id: str
    kind: str
    description: str
    params: Mapping[str, Any] = field(default_factory=dict)
    severity: str = "hard"
    source: str = "human"

    def __post_init__(self) -> None:
        object.__setattr__(self, "params", _frozen_mapping(self.params))
        if self.kind not in SUPPORTED_RULES:
            raise ValueError(f"unsupported rule kind: {self.kind}")
        if self.severity not in {"hard", "soft"}:
            raise ValueError("rule severity must be 'hard' or 'soft'")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Rule":
        return cls(
            id=str(value["id"]),
            kind=str(value["kind"]),
            description=str(value.get("description", value["id"])),
            params=value.get("params", {}),
            severity=str(value.get("severity", "hard")),
            source=str(value.get("source", "human")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "description": self.description,
            "params": dict(self.params),
            "severity": self.severity,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class Contract:
    """An immutable assume/guarantee-inspired agreement between principals."""

    id: str
    name: str
    issuer: str
    subject: str
    intent: str
    permissions: frozenset[str]
    resources: frozenset[str]
    limits: Mapping[str, float]
    rules: tuple[Rule, ...] = ()
    assumptions: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    parent_id: str | None = None
    parent_digest: str | None = None
    version: int = 1
    status: str = "active"
    seal: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "permissions", frozenset(self.permissions))
        object.__setattr__(self, "resources", frozenset(self.resources))
        object.__setattr__(self, "limits", _frozen_mapping(self.limits))
        object.__setattr__(self, "rules", tuple(self.rules))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "metrics", tuple(self.metrics))
        if self.version < 1:
            raise ValueError("contract version must be positive")
        if self.status not in {"proposed", "active", "retired"}:
            raise ValueError("unknown contract lifecycle status")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Contract":
        return cls(
            id=str(value["id"]),
            name=str(value.get("name", value["id"])),
            issuer=str(value["issuer"]),
            subject=str(value["subject"]),
            intent=str(value.get("intent", "")),
            permissions=frozenset(map(str, value.get("permissions", []))),
            resources=frozenset(map(str, value.get("resources", ["*"]))),
            limits={str(k): float(v) for k, v in value.get("limits", {}).items()},
            rules=tuple(Rule.from_dict(item) for item in value.get("rules", [])),
            assumptions=tuple(map(str, value.get("assumptions", []))),
            metrics=tuple(map(str, value.get("metrics", []))),
            parent_id=value.get("parent_id"),
            parent_digest=value.get("parent_digest"),
            version=int(value.get("version", 1)),
            status=str(value.get("status", "active")),
            seal=value.get("seal"),
        )

    def payload(self) -> dict[str, Any]:
        """Canonical content covered by the digest (the seal itself is excluded)."""
        return {
            "id": self.id,
            "name": self.name,
            "issuer": self.issuer,
            "subject": self.subject,
            "intent": self.intent,
            "permissions": sorted(self.permissions),
            "resources": sorted(self.resources),
            "limits": dict(self.limits),
            "rules": [rule.to_dict() for rule in self.rules],
            "assumptions": list(self.assumptions),
            "metrics": list(self.metrics),
            "parent_id": self.parent_id,
            "parent_digest": self.parent_digest,
            "version": self.version,
            "status": self.status,
        }

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.payload()).encode()).hexdigest()

    @property
    def is_sealed(self) -> bool:
        return self.seal is not None and self.seal == self.digest


@dataclass(frozen=True, slots=True)
class Event:
    """A proposed or observed action in an agent execution trace."""

    time: float
    actor: str
    action: str
    resource: str = "*"
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _frozen_mapping(self.data))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Event":
        return cls(
            time=float(value["time"]),
            actor=str(value["actor"]),
            action=str(value["action"]),
            resource=str(value.get("resource", "*")),
            data=value.get("data", {}),
        )


def load_bundle(path: str | Path) -> tuple[Contract, ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    values = raw.get("contracts", raw) if isinstance(raw, dict) else raw
    if not isinstance(values, list):
        raise ValueError("contract bundle must contain a 'contracts' list")
    return tuple(Contract.from_dict(item) for item in values)


def load_trace(path: str | Path) -> tuple[Event, ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    values = raw.get("events", raw) if isinstance(raw, dict) else raw
    if not isinstance(values, list):
        raise ValueError("trace must contain an 'events' list")
    return tuple(Event.from_dict(item) for item in values)


def contract_map(contracts: Iterable[Contract]) -> dict[str, Contract]:
    result: dict[str, Contract] = {}
    for contract in contracts:
        if contract.id in result:
            raise ValueError(f"duplicate contract id: {contract.id}")
        result[contract.id] = contract
    return result


def seal_contract(contract: Contract) -> Contract:
    """Return an immutable copy whose seal covers its current payload."""
    return replace(contract, seal=contract.digest)
