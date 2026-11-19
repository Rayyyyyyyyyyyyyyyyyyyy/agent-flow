"""Add two non-negative integers."""
import sys

a, b = int(sys.argv[1]), int(sys.argv[2])
if a < 0 or b < 0:
    print("error: negative input")
    sys.exit(1)
print(a + b)
