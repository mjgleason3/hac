"""Render HAC's small rule vocabulary as familiar formal notations."""

from __future__ import annotations

from .model import Rule


def formula(rule: Rule) -> str:
    """Return an explanatory formula; monitoring semantics live in firewall.py."""
    p = rule.params
    match rule.kind:
        case "forbid":
            return f"LTL  G !action({p['action']})"
        case "requires_before":
            return f"PTL  G(action({p['action']}) -> O action({p['required']}))"
        case "response_within":
            return (
                f"MTL  G(action({p['trigger']}) -> "
                f"F_[0,{float(p['within_seconds']):g}] action({p['response']}))"
            )
        case "field_limit":
            return (
                f"FOL  forall e. action(e)={p.get('action', '*')} -> "
                f"{p['field']}(e) {p.get('op', '<=')} {p['value']}"
            )
        case "cumulative_limit":
            return f"SMT  sum({p['field']}) <= {p['max']}"
        case "count_limit":
            return f"SMT  count(action={p['action']}) <= {p['max']}"
        case _:
            raise ValueError(f"unsupported rule kind: {rule.kind}")

