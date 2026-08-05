"""One-service facade for managing an organization-wide contract graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .authority import Keyring
from .firewall import ContractFirewall
from .hierarchy import HierarchyVerifier, ValidationIssue
from .ledger import ContractLedger
from .model import Contract


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    contracts: int
    roots: int
    active: int
    subjects: tuple[str, ...]
    hard_rules: int
    soft_rules: int
    ledger_valid: bool


class ContractManager:
    """Validate, activate, inspect, and enforce a complete contract portfolio."""

    def __init__(self, contracts: Iterable[Contract], *, keyring: Keyring | None = None):
        self._contracts = tuple(contracts)
        self.verifier = HierarchyVerifier(self._contracts)
        self.verifier.assert_valid()
        self.keyring = keyring
        self.ledger = ContractLedger()
        for contract in self._activation_order():
            if contract.status == "active":
                self.ledger.activate(contract, approved_by=contract.issuer)

    def firewall(self, contract_id: str) -> ContractFirewall:
        return ContractFirewall(self._contracts, contract_id, keyring=self.keyring)

    def assess(self, candidate: Contract) -> tuple[ValidationIssue, ...]:
        """Validate a proposal without mutating the active portfolio."""
        portfolio = tuple(item for item in self._contracts if item.id != candidate.id) + (candidate,)
        return HierarchyVerifier(portfolio).validate()

    def summary(self) -> PortfolioSummary:
        rules = [rule for contract in self._contracts for rule in contract.rules]
        return PortfolioSummary(
            contracts=len(self._contracts),
            roots=sum(contract.parent_id is None for contract in self._contracts),
            active=sum(contract.status == "active" for contract in self._contracts),
            subjects=tuple(sorted({contract.subject for contract in self._contracts})),
            hard_rules=sum(rule.severity == "hard" for rule in rules),
            soft_rules=sum(rule.severity == "soft" for rule in rules),
            ledger_valid=self.ledger.verify(),
        )

    def _activation_order(self) -> tuple[Contract, ...]:
        return tuple(
            sorted(
                self._contracts,
                key=lambda contract: len(self.verifier.ancestors(contract.id)),
            )
        )

