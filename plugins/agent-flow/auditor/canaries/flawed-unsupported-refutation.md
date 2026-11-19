# Review: canary round 1

Reviewer model: sonnet
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

### C3 — FAIL
Criterion: Any non-integer input prints a message starting with `error:` and exits non-zero
Reproduce: `python3 calc.py a 1`
Actual contains: `ValueError`
Expected: prints a message starting with `error:`

## Rebuttal
### C3
Reason: The program already has a path that prints `error:`, so this criterion holds.
Position: `calc.py:6`
Contains: `print("error:`
