"""Compositional validation for a hierarchy of agent contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .model import Contract, Rule, contract_map


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    contract_id: str
    message: str


class HierarchyVerifier:
    """Proves the prototype's structural attenuation invariants by inspection."""

    def __init__(self, contracts: Iterable[Contract]):
        self.contracts = contract_map(contracts)

    def ancestors(self, contract_id: str) -> tuple[Contract, ...]:
        if contract_id not in self.contracts:
            raise KeyError(contract_id)
        chain: list[Contract] = []
        seen: set[str] = set()
        current = self.contracts[contract_id]
        while current.parent_id is not None:
            if current.id in seen:
                raise ValueError(f"cycle detected at {current.id}")
            seen.add(current.id)
            parent = self.contracts.get(current.parent_id)
            if parent is None:
                raise ValueError(f"missing parent {current.parent_id} for {current.id}")
            chain.append(parent)
            current = parent
        chain.reverse()
        return tuple(chain)

    def effective_rules(self, contract_id: str) -> tuple[Rule, ...]:
        chain = (*self.ancestors(contract_id), self.contracts[contract_id])
        rules: dict[str, Rule] = {}
        for contract in chain:
            for rule in contract.rules:
                existing = rules.get(rule.id)
                if existing is not None and existing != rule:
                    raise ValueError(f"rule {rule.id} is redefined by {contract.id}")
                rules[rule.id] = rule
        return tuple(rules.values())

    def effective_permissions(self, contract_id: str) -> frozenset[str]:
        contract = self.contracts[contract_id]
        return contract.permissions

    def effective_limits(self, contract_id: str) -> dict[str, float]:
        """Return the tightest inherited limit for every allocation dimension."""
        result: dict[str, float] = {}
        for contract in (*self.ancestors(contract_id), self.contracts[contract_id]):
            for name, amount in contract.limits.items():
                result[name] = min(result.get(name, amount), amount)
        return result

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_links())
        issues.extend(self._validate_cycles())
        issues.extend(self._validate_sibling_budgets())
        return tuple(issues)

    def assert_valid(self) -> None:
        issues = self.validate()
        if issues:
            summary = "; ".join(f"{i.code}: {i.message}" for i in issues)
            raise ValueError(summary)

    def _validate_links(self) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for contract in self.contracts.values():
            if contract.status == "active" and not contract.is_sealed:
                issues.append(
                    ValidationIssue(
                        "INVALID_SEAL",
                        contract.id,
                        "active contract content does not match its seal",
                    )
                )
            rule_ids = [rule.id for rule in contract.rules]
            if len(rule_ids) != len(set(rule_ids)):
                issues.append(
                    ValidationIssue("DUPLICATE_RULE", contract.id, "rule ids must be unique")
                )
            if contract.parent_id is None:
                if contract.parent_digest is not None:
                    issues.append(
                        ValidationIssue(
                            "ORPHAN_DIGEST", contract.id, "root contract cannot pin a parent digest"
                        )
                    )
                continue
            parent = self.contracts.get(contract.parent_id)
            if parent is None:
                issues.append(
                    ValidationIssue(
                        "MISSING_PARENT", contract.id, f"parent {contract.parent_id} is absent"
                    )
                )
                continue
            if contract.parent_digest != parent.digest:
                issues.append(
                    ValidationIssue(
                        "PARENT_DIGEST_MISMATCH",
                        contract.id,
                        "child is not pinned to the loaded parent version",
                    )
                )
            if contract.issuer != parent.subject:
                issues.append(
                    ValidationIssue(
                        "UNAUTHORIZED_ISSUER",
                        contract.id,
                        f"issuer must be its parent subject ({parent.subject})",
                    )
                )
            if not _attenuates(contract.permissions, parent.permissions):
                issues.append(
                    ValidationIssue(
                        "PERMISSION_ESCALATION",
                        contract.id,
                        "child permissions exceed its parent",
                    )
                )
            if not _attenuates(contract.resources, parent.resources):
                issues.append(
                    ValidationIssue(
                        "RESOURCE_ESCALATION", contract.id, "child resources exceed its parent"
                    )
                )
            for name, amount in contract.limits.items():
                parent_amount = parent.limits.get(name)
                if parent_amount is None or amount > parent_amount:
                    issues.append(
                        ValidationIssue(
                            "LIMIT_ESCALATION",
                            contract.id,
                            f"{name}={amount:g} exceeds its parent allocation",
                        )
                    )
            ancestor_rules: dict[str, Rule] = {}
            try:
                for ancestor in self.ancestors(contract.id):
                    ancestor_rules.update({rule.id: rule for rule in ancestor.rules})
            except ValueError:
                continue
            for rule in contract.rules:
                if rule.id in ancestor_rules and rule != ancestor_rules[rule.id]:
                    issues.append(
                        ValidationIssue(
                            "RULE_REWRITE",
                            contract.id,
                            f"child attempts to redefine inherited rule {rule.id}",
                        )
                    )
        return issues

    def _validate_cycles(self) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for contract_id in self.contracts:
            try:
                self.ancestors(contract_id)
            except ValueError as exc:
                issues.append(ValidationIssue("INVALID_HIERARCHY", contract_id, str(exc)))
        return issues

    def _validate_sibling_budgets(self) -> list[ValidationIssue]:
        """Reserved child budgets obey a conservation law at each parent."""
        issues: list[ValidationIssue] = []
        for parent in self.contracts.values():
            children = [c for c in self.contracts.values() if c.parent_id == parent.id]
            names = {name for child in children for name in child.limits}
            for name in names:
                allocated = sum(child.limits.get(name, 0.0) for child in children)
                available = parent.limits.get(name)
                if available is not None and allocated > available:
                    issues.append(
                        ValidationIssue(
                            "BUDGET_OVERALLOCATION",
                            parent.id,
                            f"children reserve {allocated:g} {name}; parent has {available:g}",
                        )
                    )
        return issues


def _attenuates(child: frozenset[str], parent: frozenset[str]) -> bool:
    return "*" in parent or child.issubset(parent)
