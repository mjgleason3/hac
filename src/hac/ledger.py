"""Append-only activation receipts for immutable contract versions."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .model import Contract


@dataclass(frozen=True, slots=True)
class ActivationRecord:
    sequence: int
    contract_id: str
    version: int
    contract_digest: str
    approved_by: str
    previous_hash: str
    record_hash: str


class ContractLedger:
    def __init__(self) -> None:
        self._records: list[ActivationRecord] = []

    @property
    def records(self) -> tuple[ActivationRecord, ...]:
        return tuple(self._records)

    def activate(self, contract: Contract, *, approved_by: str) -> ActivationRecord:
        if contract.status != "active" or not contract.is_sealed:
            raise ValueError("only sealed, active contracts can be activated")
        if approved_by != contract.issuer:
            raise ValueError("activation requires the declared issuer")
        previous = self._records[-1].record_hash if self._records else "GENESIS"
        payload = {
            "sequence": len(self._records),
            "contract_id": contract.id,
            "version": contract.version,
            "contract_digest": contract.digest,
            "approved_by": approved_by,
            "previous_hash": previous,
        }
        record_hash = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        record = ActivationRecord(**payload, record_hash=record_hash)
        self._records.append(record)
        return record

    def verify(self) -> bool:
        previous = "GENESIS"
        for record in self._records:
            payload = {
                "sequence": record.sequence,
                "contract_id": record.contract_id,
                "version": record.version,
                "contract_digest": record.contract_digest,
                "approved_by": record.approved_by,
                "previous_hash": record.previous_hash,
            }
            expected = sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if record.previous_hash != previous or record.record_hash != expected:
                return False
            previous = record.record_hash
        return True

