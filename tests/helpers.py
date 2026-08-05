from dataclasses import replace

from hac.model import Contract, Rule, seal_contract


def contract_fixture():
    root = seal_contract(
        Contract(
            id="root",
            name="Root",
            issuer="human:owner",
            subject="agent:lead",
            intent="Safe service",
            permissions=frozenset({"read", "verify", "pay", "risk", "escalate"}),
            resources=frozenset({"*"}),
            limits={"usd": 500, "actions": 20},
            rules=(
                Rule(
                    "root.verify",
                    "requires_before",
                    "Verify before pay",
                    {"required": "verify", "action": "pay"},
                ),
                Rule(
                    "root.escalate",
                    "response_within",
                    "Escalate risk",
                    {"trigger": "risk", "response": "escalate", "within_seconds": 60},
                ),
            ),
        )
    )
    child = seal_contract(
        Contract(
            id="child",
            name="Child",
            issuer="agent:lead",
            subject="agent:worker",
            intent="Bounded payments",
            permissions=frozenset({"read", "verify", "pay", "risk", "escalate"}),
            resources=frozenset({"*"}),
            limits={"usd": 200, "actions": 10},
            rules=(
                Rule(
                    "child.single",
                    "field_limit",
                    "Single payment limit",
                    {"action": "pay", "field": "usd", "op": "<=", "value": 100, "required": True},
                ),
            ),
            parent_id=root.id,
            parent_digest=root.digest,
        )
    )
    return root, child


def reseal(contract, **changes):
    return seal_contract(replace(contract, seal=None, **changes))

