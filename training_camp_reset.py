#!/usr/bin/env python3
"""
training_camp_reset.py — Restore sandbox/broken_math.py to its canonical buggy state.

Run this before each Phase 1 (MCP Escape Room) drill so that TooLoo always
encounters the three planted bugs fresh.  The file is overwritten atomically
using a temp-file + rename pattern.

Bugs restored
-------------
  BUG-1  divide()      — '//' integer division instead of '/'
  BUG-2  circle_area() — literal 3.0 instead of math.pi
  BUG-3  factorial()   — missing base-case for n == 0

Security note: no eval(), exec(), or dynamic imports.  All writes go to the
jail-scoped sandbox/ directory.  No credentials or secrets are used.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_TARGET = _ROOT / "sandbox" / "broken_math.py"

# ── The canonical buggy content ───────────────────────────────────────────────
_BUGGY_CONTENT = '''\
"""
sandbox/broken_math.py — Intentionally broken math module.

This file is the target for Phase 1 of the TooLoo Training Camp (MCP Escape
Room drill).  TooLoo's NStrokeEngine must autonomously:
  1. Read this file via MCP file_read.
  2. Detect the three planted bugs via MCP code_analyze.
  3. Write the corrected version via MCP file_write.
  4. Verify the fix by running sandbox/test_broken_math.py.

--- BUG MANIFEST (do NOT fix these manually — let TooLoo do it) ---

BUG-1  divide()     — uses integer division \'//\' instead of true division \'/\'
                       divide(7, 2) returns 3 instead of 3.5

BUG-2  circle_area() — uses the literal 3.0 instead of math.pi
                        circle_area(1) returns 3.0 instead of ≈3.14159

BUG-3  factorial()  — missing base-case for n == 0; factorial(0) recurses
                       infinitely and raises RecursionError
"""
from __future__ import annotations

import math


def divide(a: float, b: float) -> float:
    """Return a divided by b.

    BUG-1: should use / not //
    """
    if b == 0:
        raise ZeroDivisionError("divide() called with b=0")
    return a // b          # BUG-1: integer division strips decimal part


def circle_area(radius: float) -> float:
    """Return the area of a circle with the given radius.

    BUG-2: should use math.pi, not the literal 3.0
    """
    return 3.0 * radius ** 2   # BUG-2: 3.0 is not π


def factorial(n: int) -> int:
    """Return n! (n factorial).

    BUG-3: missing base-case guard for n == 0, causing infinite recursion.
    """
    return n * factorial(n - 1)   # BUG-3: no base case — RecursionError on factorial(0)


def hypotenuse(a: float, b: float) -> float:
    """Return the hypotenuse of a right triangle with legs a and b.

    This function is CORRECT — it should stay untouched.
    """
    return math.sqrt(a ** 2 + b ** 2)
'''


def reset() -> None:
    """Overwrite sandbox/broken_math.py with the canonical buggy version."""
    # Resolve and validate destination is inside sandbox/ (path-traversal guard)
    resolved = _TARGET.resolve()
    sandbox_dir = (_ROOT / "sandbox").resolve()
    if not str(resolved).startswith(str(sandbox_dir)):
        print(f"ERROR: path-traversal guard triggered — refusing to write to {resolved}",
              file=sys.stderr)
        sys.exit(1)

    # Atomic write: temp file in same directory → rename
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=sandbox_dir, prefix=".broken_math_reset_", suffix=".py"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(_BUGGY_CONTENT)
        os.replace(tmp_path, resolved)
    except Exception:
        # Clean up temp on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(f"✔  Restored {resolved.relative_to(_ROOT)} to buggy state. "
          "Ready for Phase 1 Training Camp drill.")


if __name__ == "__main__":
    reset()
