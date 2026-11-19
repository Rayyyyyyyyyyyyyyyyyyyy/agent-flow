# Review: canary round 1

Reviewer model: haiku
Reviewed commit: FIXTURE

### C1 — PASS
Criterion: Two non-negative integers print their sum (`calc.py 20 3` prints 23)
Command: `python3 calc.py 20 3`
Output contains: `23`
Command: `python3 calc.py 10 32`
Output contains: `42`

### C2 — PASS
Criterion: Any negative input prints a message starting with `error:` and exits non-zero
Command: `python3 calc.py -1 1`
Output contains: `error: negative input`
Command: `python3 calc.py -1 1`
Output contains: `[exit 1]`
Command: `python3 calc.py 1 -1`
Output contains: `error: negative input`
Command: `python3 calc.py 1 -1`
Output contains: `[exit 1]`

### C3 — PASS
Criterion: Any non-integer input prints a message starting with `error:` and exits non-zero
Command: `python3 calc.py a 1`
Output contains: `error: not an integer`
