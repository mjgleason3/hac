# Static examples

These fixtures exercise HAC without an LLM or active agent:

- `support/` — a two-level delegation with inherited temporal and budget rules;
- `research/` — a forbidden private-data action;
- `incident/` — a missed five-minute human-escalation obligation.

Run all four traces with `python -m hac demo`, or audit one explicitly:

```bash
python -m hac trace examples/support/contracts.json \
  examples/support/unsafe_trace.json --contract support.refunds
```

An unsafe trace is expected to exit non-zero. It is evidence that the monitor found
the checked violation, not that an agent was run.

