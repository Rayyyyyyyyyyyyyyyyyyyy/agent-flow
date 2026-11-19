# Review: canary round 1

Reviewer model: haiku
Reviewed commit: FIXTURE

### C1 — PASS
Criterion: Two non-negative integers print their sum (`calc.py 20 3` prints 23)
Command: `python3 calc.py 20 3`
Output contains: `23`
Command: `python3 calc.py 10 32`
Output contains: `42`

### C2 – PASS
Criterion: Any negative input prints a message starting with `error:` and exits non-zero
The program checks for negative input on line 5.

### C3 — FAIL
Criterion: Any non-integer input prints a message starting with `error:` and exits non-zero
Reproduce: `python3 calc.py a 1`
Actual contains: `ValueError`
Expected: prints a message starting with `error:`
