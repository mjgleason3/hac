"""Command-line interface for the HAC prototype."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .benchmark import run_benchmark
from .compiler import RequirementCompiler
from .firewall import ContractFirewall
from .formal import formula
from .hierarchy import HierarchyVerifier
from .model import load_bundle, load_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hac", description="Hierarchical Agent Contracts prototype"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate hierarchy, seals, and attenuation")
    validate.add_argument("bundle", type=Path)
    trace = sub.add_parser("trace", help="audit a static action trace")
    trace.add_argument("bundle", type=Path)
    trace.add_argument("trace", type=Path)
    trace.add_argument("--contract", required=True)
    trace.add_argument("--open", action="store_true", help="leave future obligations pending")
    compile_cmd = sub.add_parser("compile", help="compile a controlled-English requirement")
    compile_cmd.add_argument("requirement")
    benchmark = sub.add_parser("benchmark", help="run the deterministic synthetic comparison")
    benchmark.add_argument("--json", action="store_true")
    sub.add_parser("demo", help="run all checked-in static trace examples")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args.bundle)
        if args.command == "trace":
            return _trace(args.bundle, args.trace, args.contract, complete=not args.open)
        if args.command == "compile":
            return _compile(args.requirement)
        if args.command == "benchmark":
            return _benchmark(as_json=args.json)
        if args.command == "demo":
            return _demo()
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def _validate(path: Path) -> int:
    verifier = HierarchyVerifier(load_bundle(path))
    issues = verifier.validate()
    if not issues:
        print(f"PASS  {len(verifier.contracts)} contracts form a valid attenuating hierarchy")
        for contract in verifier.contracts.values():
            print(f"  {contract.id}@{contract.version}  sha256:{contract.digest[:12]}")
        return 0
    print(f"FAIL  {len(issues)} hierarchy issue(s)")
    for issue in issues:
        print(f"  {issue.code:<28} {issue.contract_id}: {issue.message}")
    return 1


def _trace(bundle: Path, trace: Path, contract_id: str, *, complete: bool) -> int:
    firewall = ContractFirewall(load_bundle(bundle), contract_id)
    report = firewall.audit_trace(load_trace(trace), complete=complete)
    status = "PASS" if report.passed else "FAIL"
    print(f"{status}  {trace.name} · {report.events} events · contract {contract_id}")
    for item in report.violations:
        print(f"  {item.severity.upper():<4} {item.rule_id}: {item.message}")
    for item in report.pending_obligations:
        print(f"  WAIT {item.rule_id}: {item.message}")
    return 0 if report.passed else 1


def _compile(text: str) -> int:
    compiled = RequirementCompiler().compile(text)
    print(compiled.formula)
    print(json.dumps(compiled.rule.to_dict(), indent=2))
    return 0


def _benchmark(*, as_json: bool) -> int:
    results = run_benchmark()
    if as_json:
        print(json.dumps([asdict(result) for result in results], indent=2))
        return 0
    print("Synthetic fixture — not a real-agent efficacy claim")
    print("approach          prevented   false blocks   coverage   delegation   mean µs")
    for result in results:
        print(
            f"{result.approach:<17} "
            f"{result.unsafe_prevented}/{result.unsafe_total:<9} "
            f"{result.false_blocks}/{result.safe_total:<12} "
            f"{result.requirement_coverage}/{result.requirement_total:<8} "
            f"{result.delegation_faults_detected}/{result.delegation_faults_total:<10} "
            f"{result.mean_decision_us:>7.2f}"
        )
    return 0


def _demo() -> int:
    base = Path("examples")
    runs = (
        (base / "support" / "contracts.json", base / "support" / "safe_trace.json", "support.refunds"),
        (base / "support" / "contracts.json", base / "support" / "unsafe_trace.json", "support.refunds"),
        (base / "research" / "contracts.json", base / "research" / "privacy_trace.json", "research.root"),
        (base / "incident" / "contracts.json", base / "incident" / "late_page_trace.json", "incident.root"),
    )
    exit_code = 0
    for bundle, trace, contract_id in runs:
        code = _trace(bundle, trace, contract_id, complete=True)
        print()
        if trace.name == "safe_trace.json" and code:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
