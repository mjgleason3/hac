"""Hierarchical Agent Contracts (HAC) prototype."""

from .authority import Capability, Keyring
from .compiler import RequirementCompiler
from .firewall import ContractFirewall, Decision, TraceReport
from .hierarchy import HierarchyVerifier, ValidationIssue
from .manager import ContractManager
from .model import Contract, Event, Rule, load_bundle, load_trace, seal_contract

__all__ = [
    "Capability",
    "Contract",
    "ContractFirewall",
    "ContractManager",
    "Decision",
    "Event",
    "HierarchyVerifier",
    "Keyring",
    "RequirementCompiler",
    "Rule",
    "TraceReport",
    "ValidationIssue",
    "load_bundle",
    "load_trace",
    "seal_contract",
]

__version__ = "0.1.0"
