"""A tiny, inspectable capability-delegation model for the HAC prototype."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import json
import secrets
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Capability:
    id: str
    issuer: str
    subject: str
    actions: frozenset[str]
    resources: frozenset[str]
    expires_at: float
    remaining_depth: int
    contract_digest: str
    parent_id: str | None = None
    signature: str = ""

    def payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "issuer": self.issuer,
            "subject": self.subject,
            "actions": sorted(self.actions),
            "resources": sorted(self.resources),
            "expires_at": self.expires_at,
            "remaining_depth": self.remaining_depth,
            "contract_digest": self.contract_digest,
            "parent_id": self.parent_id,
        }


class Keyring:
    """Demo HMAC keyring. Production deployments should use asymmetric KMS-backed keys."""

    def __init__(self, keys: dict[str, bytes] | None = None):
        self._keys = dict(keys or {})

    def add(self, principal: str, key: bytes | None = None) -> None:
        self._keys[principal] = key or secrets.token_bytes(32)

    def sign(self, capability: Capability) -> Capability:
        key = self._keys.get(capability.issuer)
        if key is None:
            raise ValueError(f"no signing key for {capability.issuer}")
        message = json.dumps(capability.payload(), sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(key, message, sha256).hexdigest()
        return replace(capability, signature=signature)

    def verify_signature(self, capability: Capability) -> bool:
        key = self._keys.get(capability.issuer)
        if key is None:
            return False
        unsigned = replace(capability, signature="")
        expected = self.sign(unsigned).signature
        return hmac.compare_digest(expected, capability.signature)

    def mint(
        self,
        *,
        issuer: str,
        subject: str,
        actions: Iterable[str],
        resources: Iterable[str],
        expires_at: float,
        remaining_depth: int,
        contract_digest: str,
    ) -> Capability:
        capability = Capability(
            id=secrets.token_hex(8),
            issuer=issuer,
            subject=subject,
            actions=frozenset(actions),
            resources=frozenset(resources),
            expires_at=expires_at,
            remaining_depth=remaining_depth,
            contract_digest=contract_digest,
        )
        return self.sign(capability)

    def delegate(
        self,
        parent: Capability,
        *,
        issuer: str,
        subject: str,
        actions: Iterable[str],
        resources: Iterable[str],
        expires_at: float,
        contract_digest: str,
    ) -> Capability:
        child_actions = frozenset(actions)
        child_resources = frozenset(resources)
        if not self.verify_signature(parent):
            raise ValueError("parent capability signature is invalid")
        if issuer != parent.subject:
            raise ValueError("only the parent subject may delegate")
        if parent.remaining_depth < 1:
            raise ValueError("delegation depth exhausted")
        if not _covers(parent.actions, child_actions) or not _covers(parent.resources, child_resources):
            raise ValueError("delegation must attenuate authority")
        if expires_at > parent.expires_at:
            raise ValueError("delegation cannot extend expiry")
        child = Capability(
            id=secrets.token_hex(8),
            issuer=issuer,
            subject=subject,
            actions=child_actions,
            resources=child_resources,
            expires_at=expires_at,
            remaining_depth=parent.remaining_depth - 1,
            contract_digest=contract_digest,
            parent_id=parent.id,
        )
        return self.sign(child)

    def authorize(
        self,
        chain: Iterable[Capability],
        *,
        subject: str,
        action: str,
        resource: str,
        now: float,
        contract_digest: str,
    ) -> tuple[bool, str]:
        capabilities = tuple(chain)
        if not capabilities:
            return False, "missing capability chain"
        for index, capability in enumerate(capabilities):
            if not self.verify_signature(capability):
                return False, f"invalid signature on capability {capability.id}"
            if capability.expires_at < now:
                return False, f"capability {capability.id} has expired"
            if index:
                parent = capabilities[index - 1]
                if capability.parent_id != parent.id or capability.issuer != parent.subject:
                    return False, "broken delegation chain"
                if not _covers(parent.actions, capability.actions) or not _covers(
                    parent.resources, capability.resources
                ):
                    return False, "delegated authority expands its parent"
        leaf = capabilities[-1]
        if leaf.subject != subject:
            return False, "capability subject does not match actor"
        if not _covers(leaf.actions, frozenset({action})):
            return False, "action is outside delegated authority"
        if not _covers(leaf.resources, frozenset({resource})):
            return False, "resource is outside delegated authority"
        if leaf.contract_digest != contract_digest:
            return False, "capability is bound to a different contract version"
        return True, "authorized"


def _covers(parent: frozenset[str], child: frozenset[str]) -> bool:
    return "*" in parent or child.issubset(parent)

