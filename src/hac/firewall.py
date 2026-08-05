"""Pre-action enforcement and offline trace verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .authority import Capability, Keyring
from .hierarchy import HierarchyVerifier
from .model import Contract, Event, Rule


@dataclass(frozen=True, slots=True)
class Violation:
    code: str
    rule_id: str
    message: str
    severity: str = "hard"
    event_index: int | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    contract_id: str
    event: Event
    violations: tuple[Violation, ...]
    evaluated_rules: tuple[str, ...]

    @property
    def outcome(self) -> str:
        if not self.allowed:
            return "BLOCK"
        if self.violations:
            return "ALLOW_WITH_WARNING"
        return "ALLOW"


@dataclass(frozen=True, slots=True)
class TraceReport:
    contract_id: str
    events: int
    violations: tuple[Violation, ...]
    pending_obligations: tuple[Violation, ...]

    @property
    def passed(self) -> bool:
        return not any(item.severity == "hard" for item in self.violations)


class ContractFirewall:
    """Evaluate actions outside the operating agent's decision loop.

    The caller must place this object in a trusted mediation path. This library
    cannot stop an agent that retains a second, unmediated route to a tool.
    """

    def __init__(
        self,
        contracts: Iterable[Contract],
        contract_id: str,
        *,
        keyring: Keyring | None = None,
    ):
        self.verifier = HierarchyVerifier(contracts)
        self.verifier.assert_valid()
        self.contract = self.verifier.contracts[contract_id]
        self.rules = self.verifier.effective_rules(contract_id)
        self.limits = self.verifier.effective_limits(contract_id)
        self.keyring = keyring
        self._snapshot = tuple(
            (contract.id, contract.digest) for contract in (*self.verifier.ancestors(contract_id), self.contract)
        )

    def preflight(
        self,
        event: Event,
        history: Sequence[Event] = (),
        *,
        capability_chain: Iterable[Capability] = (),
    ) -> Decision:
        self._assert_snapshot()
        violations: list[Violation] = []
        if event.actor != self.contract.subject:
            violations.append(
                Violation(
                    "ACTOR_MISMATCH",
                    "authority.actor",
                    f"{event.actor} is not the contract subject {self.contract.subject}",
                )
            )
        if not _contains(self.contract.permissions, event.action):
            violations.append(
                Violation(
                    "ACTION_NOT_PERMITTED",
                    "authority.action",
                    f"{event.action} is outside the contract permission set",
                )
            )
        if not _contains(self.contract.resources, event.resource):
            violations.append(
                Violation(
                    "RESOURCE_NOT_PERMITTED",
                    "authority.resource",
                    f"{event.resource} is outside the contract resource set",
                )
            )
        if self.keyring is not None:
            authorized, reason = self.keyring.authorize(
                capability_chain,
                subject=event.actor,
                action=event.action,
                resource=event.resource,
                now=event.time,
                contract_digest=self.contract.digest,
            )
            if not authorized:
                violations.append(Violation("CAPABILITY_DENIED", "authority.chain", reason))
        violations.extend(self._evaluate_allocations(event, history))
        for rule in self.rules:
            violation = _evaluate_immediate(rule, event, history)
            if violation is not None:
                violations.append(violation)
        allowed = not any(item.severity == "hard" for item in violations)
        return Decision(
            allowed=allowed,
            contract_id=self.contract.id,
            event=event,
            violations=tuple(violations),
            evaluated_rules=tuple(rule.id for rule in self.rules),
        )

    def _evaluate_allocations(
        self, event: Event, history: Sequence[Event]
    ) -> tuple[Violation, ...]:
        violations: list[Violation] = []
        for name, maximum in self.limits.items():
            if name == "actions":
                used = len(history) + 1
            else:
                used = sum(_number(item.data.get(name, 0)) for item in (*history, event))
            if used > maximum:
                violations.append(
                    Violation(
                        "ALLOCATION_EXCEEDED",
                        f"allocation.{name}",
                        f"{name} use {used:g} exceeds delegated allocation {maximum:g}",
                    )
                )
        return tuple(violations)

    def audit_trace(
        self,
        events: Iterable[Event],
        *,
        complete: bool = True,
        capability_chain: Iterable[Capability] = (),
    ) -> TraceReport:
        ordered = tuple(sorted(events, key=lambda item: item.time))
        history: list[Event] = []
        violations: list[Violation] = []
        for index, event in enumerate(ordered):
            decision = self.preflight(event, history, capability_chain=capability_chain)
            violations.extend(
                Violation(
                    item.code,
                    item.rule_id,
                    item.message,
                    item.severity,
                    event_index=index,
                )
                for item in decision.violations
            )
            history.append(event)
        pending: list[Violation] = []
        for rule in self.rules:
            if rule.kind != "response_within":
                continue
            found, waiting = _response_violations(rule, ordered, complete=complete)
            violations.extend(found)
            pending.extend(waiting)
        return TraceReport(
            contract_id=self.contract.id,
            events=len(ordered),
            violations=tuple(violations),
            pending_obligations=tuple(pending),
        )

    def _assert_snapshot(self) -> None:
        current = tuple(
            (contract.id, contract.digest)
            for contract in (*self.verifier.ancestors(self.contract.id), self.contract)
        )
        if current != self._snapshot:
            raise RuntimeError("activated contract snapshot changed")


def _evaluate_immediate(rule: Rule, event: Event, history: Sequence[Event]) -> Violation | None:
    p = rule.params
    message: str | None = None
    code = "RULE_VIOLATION"
    if rule.kind == "forbid" and event.action == p["action"]:
        message = f"forbidden action attempted: {event.action}"
    elif rule.kind == "requires_before" and event.action == p["action"]:
        required = str(p["required"])
        same_resource = bool(p.get("same_resource", True))
        satisfied = any(
            prior.action == required
            and prior.time <= event.time
            and (not same_resource or prior.resource == event.resource)
            for prior in history
        )
        if not satisfied:
            message = f"{required} must occur before {event.action}"
    elif rule.kind == "field_limit" and _applies_to_action(p, event):
        field = str(p["field"])
        if field not in event.data:
            if p.get("required", False):
                message = f"required field {field} is missing"
        elif not _compare(event.data[field], str(p.get("op", "<=")), p["value"]):
            message = f"{field}={event.data[field]} violates {p.get('op', '<=')} {p['value']}"
    elif rule.kind == "cumulative_limit":
        field = str(p["field"])
        total = sum(_number(item.data.get(field, 0)) for item in (*history, event))
        if total > float(p["max"]):
            message = f"cumulative {field}={total:g} exceeds {float(p['max']):g}"
    elif rule.kind == "count_limit" and event.action == p["action"]:
        count = sum(item.action == event.action for item in history) + 1
        if count > int(p["max"]):
            message = f"{event.action} count {count} exceeds {int(p['max'])}"
    if message is None:
        return None
    return Violation(code, rule.id, message, rule.severity)


def _response_violations(
    rule: Rule, events: Sequence[Event], *, complete: bool
) -> tuple[list[Violation], list[Violation]]:
    p = rule.params
    found: list[Violation] = []
    pending: list[Violation] = []
    horizon = events[-1].time if events else 0.0
    for index, trigger in enumerate(events):
        if trigger.action != p["trigger"]:
            continue
        deadline = trigger.time + float(p["within_seconds"])
        same_resource = bool(p.get("same_resource", True))
        satisfied = any(
            response.action == p["response"]
            and trigger.time <= response.time <= deadline
            and (not same_resource or response.resource == trigger.resource)
            for response in events[index + 1 :]
        )
        if satisfied:
            continue
        item = Violation(
            "DEADLINE_MISSED" if complete or horizon > deadline else "OBLIGATION_PENDING",
            rule.id,
            f"{p['response']} did not follow {p['trigger']} within {float(p['within_seconds']):g}s",
            rule.severity,
            event_index=index,
        )
        if complete or horizon > deadline:
            found.append(item)
        else:
            pending.append(item)
    return found, pending


def _applies_to_action(params: dict[str, Any] | Any, event: Event) -> bool:
    action = params.get("action", "*")
    return action == "*" or action == event.action


def _compare(left: Any, op: str, right: Any) -> bool:
    try:
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "==":
            return left == right
    except TypeError:
        return False
    raise ValueError(f"unsupported operator: {op}")


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _contains(values: frozenset[str], candidate: str) -> bool:
    return "*" in values or candidate in values
