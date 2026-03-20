"""
engine/mcp_manager.py — MCP (Model Context Protocol) Tool Manager.

Implements the MCP tool-discovery + dispatch pattern without requiring an
external MCP server.  Tools are registered at import time and discoverable
via ``MCPManager.manifest()``.  All invocations are synchronous and the
outputs are sanitised before being returned to the engine.

Registered tools (MCP URI → handler):
  mcp://tooloo/file_read    — Read workspace file, return content + line count
  mcp://tooloo/file_write   — Write file inside workspace (escape-hatch guard)
  mcp://tooloo/code_analyze — Parse traceback / code snippet for error patterns
  mcp://tooloo/web_lookup   — Retrieve structured SOTA signals by keyword
  mcp://tooloo/run_tests    — Run pytest on a test module, return pass/fail
  mcp://tooloo/read_error   — Parse error string → structured {type, message, hint}

Security:
  - File paths jail-checked to WORKSPACE_ROOT (no ../ traversal allowed).
  - file_write rejects paths outside workspace and forbidden extensions.
  - run_tests rejects modules that escape the tests/ directory.
  - All output strings are length-capped and stripped of control characters.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Workspace root (one level up from this file) ──────────────────────────────
_WORKSPACE_ROOT: Path = Path(__file__).resolve().parents[1]

# ── Tool URI prefix ───────────────────────────────────────────────────────────
_MCP_PREFIX = "mcp://tooloo/"

# ── Output size cap ───────────────────────────────────────────────────────────
# raised from 8 KB → 64 KB → 128 KB to handle large engine files (e.g. router.py ~66 KB)
_MAX_OUTPUT_CHARS: int = 131_072

# ── Forbidden write extensions ────────────────────────────────────────────────
_FORBIDDEN_WRITE_EXTS: frozenset[str] = frozenset(
    {".sh", ".bash", ".zsh", ".bat", ".exe", ".bin", ".so", ".dylib"})

# ── SOTA signal catalogue for web_lookup ──────────────────────────────────────
_SOTA_CATALOGUE: dict[str, list[str]] = {
    "zero-latency": [
        "Zero-latency audio requires lock-free ring-buffers (SPSC) — CPython GIL prevents "
        "true lock-free; use ctypes/cffi with native ring buffer",
        "Python threading for real-time DSP is limited by GIL — Cython with nogil or "
        "PyAudio CFFI bindings are production approaches",
        "numpy.frombuffer on shared mmap bypasses copy overhead; use sounddevice callback mode",
    ],
    "dsp": [
        "scipy.signal / librosa are SOTA for offline DSP; for real-time prefer sounddevice "
        "+ numpy ring buffers",
        "Thread priority elevation (os.sched_setscheduler on Linux) critical for <10ms DSP latency",
        "ASIO/CoreAudio/ALSA each have different Python binding maturity — sounddevice wraps all three",
    ],
    "async": [
        "asyncio event loop + ThreadPoolExecutor is canonical for CPU-bound work inside async code",
        "anyio provides unified async backend (asyncio/trio); preferred for library code",
        "asyncio.TaskGroup (3.11+) is preferred over gather() for structured concurrency",
    ],
    "python": [
        "Python 3.12 sub-interpreters (PEP 734) provide true parallelism without multiprocessing overhead",
        "Free-threaded Python 3.13 (--disable-gil) is production-experimental in 2026",
        "Ruff v0.4 is the dominant linter+formatter in 2026 — replaces flake8/black/isort",
    ],
    "security": [
        "OWASP Top 10 2025 #1 is Broken Object-Level Authorization — validate ownership on every fetch",
        "Parameterized queries (SQLAlchemy Core / psycopg3) are mandatory — no string concatenation SQL",
        "Secrets management: Vault/AWS/GCP Secret Manager — never in env vars in production",
    ],
    "test": [
        "pytest-xdist parallelizes test execution across CPU cores — critical for suites > 500 tests",
        "hypothesis property-based testing catches edge cases missed by hand-written examples",
        "testcontainers-python spins up real DBs/queues in Docker for integration tests",
    ],
    "build": [
        "FastAPI + Pydantic v2 are the production standard for async Python services in 2026",
        "OpenTelemetry is the de-facto distributed tracing standard; instrument from day one",
        "Structured logging with correlation IDs (JSON + trace_id) is table stakes for observability",
    ],
    "default": [
        "FastAPI + Pydantic v2 are the production standard for async Python services in 2026",
        "OpenTelemetry is the de-facto distributed tracing standard; instrument from day one",
        "Structured logging with correlation IDs (JSON + trace_id) is table stakes for observability",
    ],
}


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class MCPToolSpec:
    """Describes one registered MCP tool."""

    uri: str
    name: str
    description: str
    parameters: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class MCPCallResult:
    """Result of one MCP tool invocation."""

    uri: str
    success: bool
    output: Any
    error: str | None = None
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "truncated": self.truncated,
        }


# ── Security helpers ──────────────────────────────────────────────────────────


def _jail_path(raw_path: str) -> Path:
    """Resolve path and assert it is inside _WORKSPACE_ROOT.

    Raises ``ValueError`` on any attempted path traversal.
    """
    resolved = (_WORKSPACE_ROOT / raw_path).resolve()
    if not str(resolved).startswith(str(_WORKSPACE_ROOT)):
        raise ValueError(
            f"Path traversal rejected: '{raw_path}' resolves outside workspace."
        )
    return resolved


def _sanitise(text: str, max_chars: int = _MAX_OUTPUT_CHARS) -> tuple[str, bool]:
    """Strip control characters, cap length; return (clean_text, was_truncated)."""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    if len(clean) > max_chars:
        return clean[:max_chars] + "\n…[truncated]", True
    return clean, False


# ── Tool implementations ───────────────────────────────────────────────────────


def _tool_file_read(path: str, **_: Any) -> dict[str, Any]:
    resolved = _jail_path(path)
    content = resolved.read_text(encoding="utf-8", errors="replace")
    text, truncated = _sanitise(content)
    return {
        "path": str(resolved.relative_to(_WORKSPACE_ROOT)),
        "content": text,
        "lines": text.count("\n") + 1,
        "truncated": truncated,
    }


def _tool_file_write(path: str, content: str, **_: Any) -> dict[str, Any]:
    resolved = _jail_path(path)
    if resolved.suffix.lower() in _FORBIDDEN_WRITE_EXTS:
        raise ValueError(
            f"Write to '{resolved.suffix}' extension is not permitted."
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return {
        "path": str(resolved.relative_to(_WORKSPACE_ROOT)),
        "bytes_written": len(content.encode()),
    }


def _tool_code_analyze(
    code: str = "",
    file_path: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Static analysis: extract imports, detect error patterns, count LOC, and build AST symbol map.

    When ``file_path`` is supplied (workspace-relative), the file is read and
    parsed in addition to (or instead of) the ``code`` string.  The ``symbol_map``
    key is populated using Python's built-in ``ast`` module — zero tokens, zero
    hallucination.  Ghost branches can consume this map to know exact line ranges
    before issuing a ``patch_apply`` call.

    symbol_map entries:
      {"type": "class"|"function"|"method", "name": str, "parent": str|None,
       "lines": [start, end], "signature": str, "docstring": str}
    """
    import ast as _ast

    # ── Resolve source text ───────────────────────────────────────────────────
    if file_path:
        try:
            resolved = _jail_path(file_path)
            source = resolved.read_text(encoding="utf-8", errors="replace")
        except Exception:
            source = code
    else:
        source = code

    lines = source.splitlines()

    # ── Classic heuristic analysis ─────────────────────────────────────────
    imports = [
        ln.strip() for ln in lines
        if ln.strip().startswith(("import ", "from "))
    ]
    error_patterns = [
        ln.strip() for ln in lines
        if re.search(r"\b(raise|Error|Exception|Traceback)\b", ln)
    ]
    has_async = any("async " in ln or "await " in ln for ln in lines)

    # ── AST symbol map ─────────────────────────────────────────────────────
    symbol_map: list[dict[str, Any]] = []
    try:
        tree = _ast.parse(source)
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ClassDef):
                # Extract class-level docstring
                doc = ""
                if (
                    node.body
                    and isinstance(node.body[0], _ast.Expr)
                    and isinstance(node.body[0].value, _ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    doc = node.body[0].value.value.splitlines()[0][:120]

                symbol_map.append({
                    "type": "class",
                    "name": node.name,
                    "parent": None,
                    "lines": [node.lineno, getattr(node, "end_lineno", node.lineno)],
                    "signature": node.name,
                    "docstring": doc,
                })

                # Methods inside this class
                for item in node.body:
                    if isinstance(item, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                        args_str = ", ".join(
                            a.arg for a in item.args.args
                        )
                        method_doc = ""
                        if (
                            item.body
                            and isinstance(item.body[0], _ast.Expr)
                            and isinstance(item.body[0].value, _ast.Constant)
                            and isinstance(item.body[0].value.value, str)
                        ):
                            method_doc = item.body[0].value.value.splitlines()[
                                0][:120]
                        symbol_map.append({
                            "type": "method",
                            "name": item.name,
                            "parent": node.name,
                            "lines": [item.lineno, getattr(item, "end_lineno", item.lineno)],
                            "signature": f"{item.name}({args_str})",
                            "docstring": method_doc,
                        })

            elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                # Top-level functions only (not inside a class — those are captured above)
                # Heuristic: if the parent is Module, it's top-level
                args_str = ", ".join(a.arg for a in node.args.args)
                fn_doc = ""
                if (
                    node.body
                    and isinstance(node.body[0], _ast.Expr)
                    and isinstance(node.body[0].value, _ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    fn_doc = node.body[0].value.value.splitlines()[0][:120]
                # Skip if already captured as a method (has parent class in symbol_map)
                is_method = any(
                    s["type"] == "method" and s["name"] == node.name
                    and s["lines"][0] == node.lineno
                    for s in symbol_map
                )
                if not is_method:
                    symbol_map.append({
                        "type": "function",
                        "name": node.name,
                        "parent": None,
                        "lines": [node.lineno, getattr(node, "end_lineno", node.lineno)],
                        "signature": f"{node.name}({args_str})",
                        "docstring": fn_doc,
                    })
    except SyntaxError:
        pass  # Non-Python content or fragment — symbol_map stays empty

    return {
        "loc": len(lines),
        "imports": imports[:20],
        "error_patterns": error_patterns[:10],
        "has_async": has_async,
        "symbol_map": symbol_map,
    }


def _tool_web_lookup(query: str, **_: Any) -> dict[str, Any]:
    """Return structured SOTA signals matching the query keywords."""
    q_lower = query.lower()
    matched: list[str] = []
    for key, signals in _SOTA_CATALOGUE.items():
        if key == "default":
            continue
        if key in q_lower or any(word in q_lower for word in key.split("-")):
            matched.extend(signals)
    if not matched:
        matched = list(_SOTA_CATALOGUE["default"])
    return {
        "query": query,
        "signals": matched[:5],
        "source": "structured_catalogue",
    }


def _tool_run_tests(
    test_path: str = "",
    module: str | None = None,
    timeout: int | None = None,
    extra_args: list[str] | None = None,
    env_overrides: dict[str, str] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Run pytest on a test module inside tests/ and return verdict.

    Args:
        test_path:      Path inside tests/ to run (e.g. ``tests`` or ``tests/test_foo.py``).
        module:         Alias for test_path (legacy callers).
        timeout:        Outer subprocess timeout in seconds (default 180).
        extra_args:     Additional pytest flags, e.g. ``["--ignore=tests/test_ingestion.py"]``.
                        Each entry is appended verbatim after the test-path argument.
        env_overrides:  Dict of env var overrides for the subprocess.
                        Use ``{"TOOLOO_LIVE_TESTS": "0"}`` to force offline mode.
    """
    if not test_path and module:
        test_path = module
    if not test_path:
        raise ValueError("test_path is required.")

    resolved = _jail_path(test_path)
    tests_dir = (_WORKSPACE_ROOT / "tests").resolve()
    if not str(resolved).startswith(str(tests_dir)):
        raise ValueError("test_path must be inside the tests/ directory.")

    cmd = [sys.executable, "-m", "pytest",
           str(resolved), "--tb=short", "-q", "--timeout=30"]
    if extra_args:
        cmd.extend(extra_args)
    run_env = {**os.environ, **(env_overrides or {})}
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout or 180,
        cwd=str(_WORKSPACE_ROOT),
        env=run_env,
    )
    output, truncated = _sanitise(result.stdout + result.stderr)
    return {
        "test_path": str(resolved.relative_to(_WORKSPACE_ROOT)),
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "output": output,
        "truncated": truncated,
    }


def _tool_read_error(error_text: str, **_: Any) -> dict[str, Any]:
    """Parse a traceback or error string into structured error data."""
    lines = error_text.strip().splitlines()
    error_type = "UnknownError"
    message = error_text[:200]
    hint = ""

    for line in reversed(lines):
        m = re.match(
            r"^(\w+(?:\.\w+)*Error|\w+Exception):\s*(.+)$", line.strip())
        if m:
            error_type = m.group(1)
            message = m.group(2).strip()
            break

    _HINTS: dict[str, str] = {
        "ZeroDivision": "Check denominator before division.",
        "Import": "Verify the module is installed and in sys.path.",
        "Attribute": "Check object type and available methods.",
        "Type": "Check argument types match the function signature.",
        "Key": "Use .get() with a default or check key existence first.",
        "Timeout": "Increase timeout budget or reduce operation scope.",
        "Memory": "Reduce buffer sizes or use streaming/chunked processing.",
        "Runtime": "Review logic constraints and algorithm bounds.",
    }
    for keyword, h in _HINTS.items():
        if keyword in error_type or keyword.lower() in error_text.lower():
            hint = h
            break
    if not hint:
        hint = "Review the stack trace and check input data validity."

    file_lines = re.findall(r'File "(.+?)", line (\d+)', error_text)
    location = (
        {"file": file_lines[-1][0], "line": int(file_lines[-1][1])}
        if file_lines else None
    )
    return {
        "error_type": error_type,
        "message": message,
        "hint": hint,
        "location": location,
        "raw_truncated": len(error_text) > 2000,
    }


def _tool_spawn_process(
    branch_type: str = "fork",
    intent: str = "IDEATE",
    mandate: str = "",
    target: str = "",
    parent_branch_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    type: str | None = None,
    branch_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Emit a validated BranchSpec-compatible payload for dynamic branching."""
    normalized_type = (type or branch_type or "fork").strip().lower()
    if normalized_type not in {"fork", "clone", "share"}:
        raise ValueError("branch_type must be one of: fork, clone, share")

    mandate_text = str(kwargs.get("mandate_text") or mandate or "").strip()
    if not mandate_text:
        raise ValueError("mandate is required for spawn_process")

    payload: dict[str, Any] = {
        "branch_id": branch_id or f"spawn-{uuid.uuid4().hex[:8]}",
        "branch_type": normalized_type,
        "mandate_text": mandate_text,
        "intent": str(intent or "IDEATE").upper(),
        "target": str(target or kwargs.get("file_path") or ""),
        "parent_branch_id": parent_branch_id,
        "metadata": {
            "autonomously_spawned": True,
            "spawn_source": "mcp://tooloo/spawn_process",
            **(metadata or {}),
        },
    }
    return {
        "spawned_branch": payload,
        "message": f"Spawn request validated for {payload['intent']}:{payload['branch_type']}",
    }


def _tool_patch_apply(
    file_path: str,
    search_block: str,
    replace_block: str,
    fuzzy: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """Surgical micro-patch: locate search_block in file and replace with replace_block.

    Unlike file_write, this never rewrites the entire file — keeping the blast radius
    to the exact lines that need changing.

    When ``fuzzy=True``, whitespace is collapsed for matching to handle minor
    indentation drift common in LLM-generated search blocks.

    Security: path-traversal guarded; only workspace files allowed.
    """
    resolved = _jail_path(file_path)
    original = resolved.read_text(encoding="utf-8", errors="replace")

    if fuzzy:
        # Collapse runs of whitespace for comparison only
        def _ws_norm(s: str) -> str:
            return re.sub(r"[ \t]+", " ", s)

        norm_original = _ws_norm(original)
        norm_search = _ws_norm(search_block)
        idx = norm_original.find(norm_search)
        if idx == -1:
            raise ValueError(
                f"search_block not found in '{file_path}' (fuzzy=True). "
                "Verify the target text and try again."
            )
        # Reconstruct original offsets from normalised position
        # Walk through original, tracking normalised position vs raw position
        raw_idx = 0
        norm_pos = 0
        while norm_pos < idx and raw_idx < len(original):
            c = original[raw_idx]
            norm_c = _ws_norm(c)
            norm_pos += len(norm_c)
            raw_idx += 1
        # Match length in normalised space → find end in raw space
        raw_end = raw_idx
        match_norm_len = len(norm_search)
        accum = 0
        while accum < match_norm_len and raw_end < len(original):
            accum += len(_ws_norm(original[raw_end]))
            raw_end += 1
        patched = original[:raw_idx] + replace_block + original[raw_end:]
    else:
        if search_block not in original:
            raise ValueError(
                f"search_block not found verbatim in '{file_path}'. "
                "Use fuzzy=True for whitespace-tolerant matching."
            )
        patched = original.replace(search_block, replace_block, 1)

    resolved.write_text(patched, encoding="utf-8")
    lines_before = original.count("\n") + 1
    lines_after = patched.count("\n") + 1
    return {
        "file_path": str(resolved.relative_to(_WORKSPACE_ROOT)),
        "lines_before": lines_before,
        "lines_after": lines_after,
        "delta_lines": lines_after - lines_before,
        "fuzzy": fuzzy,
        "patched": True,
    }


def _tool_run_tests_isolated(
    file_path: str,
    patch_search: str,
    patch_replace: str,
    test_path: str,
    timeout: int | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Speculatively patch a source file, run targeted tests, then always revert.

    Enables ghost branches to validate code changes with zero blast radius:
    the original file is atomically restored in a ``finally`` block even if
    the test subprocess crashes or times out.  Tests are scoped to a single
    test file (not the full 900+ suite) for fast, targeted feedback.

    This is the sandbox crucible pattern: each speculative ghost branch can call
    this tool to race its patch against others — only the winning patch
    (first to pass tests) is promoted to the main trunk.

    Args:
        file_path:     Workspace-relative path to the source file to patch.
        patch_search:  Exact string to replace (verbatim match, ≤ 30 lines).
        patch_replace: Replacement string (the proposed fix).
        test_path:     Workspace-relative test path (must be inside tests/).
        timeout:       Subprocess timeout in seconds (default 60).

    Security: path-traversal guarded on both paths; test path jailed to tests/.
    """
    # ── Security: jail both paths ─────────────────────────────────────────
    resolved_src = _jail_path(file_path)
    resolved_test = _jail_path(test_path)
    tests_dir = (_WORKSPACE_ROOT / "tests").resolve()
    if not str(resolved_test).startswith(str(tests_dir)):
        raise ValueError("test_path must be inside the tests/ directory.")

    # ── Apply patch to real file (subprocess will import the patched version)
    original = resolved_src.read_text(encoding="utf-8", errors="replace")
    if patch_search not in original:
        raise ValueError(
            f"patch_search not found verbatim in '{file_path}'. "
            "Verify the exact text before using run_tests_isolated."
        )
    patched = original.replace(patch_search, patch_replace, 1)
    resolved_src.write_text(patched, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             str(resolved_test), "--tb=short", "-q", "--timeout=30"],
            capture_output=True,
            text=True,
            timeout=timeout or 60,
            cwd=str(_WORKSPACE_ROOT),
        )
        output, truncated = _sanitise(result.stdout + result.stderr)
        return {
            "file_path": str(resolved_src.relative_to(_WORKSPACE_ROOT)),
            "test_path": str(resolved_test.relative_to(_WORKSPACE_ROOT)),
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "output": output,
            "truncated": truncated,
            "patch_applied": True,
            "isolated": True,
        }
    finally:
        # ── Always revert — zero blast radius guarantee ────────────────────
        resolved_src.write_text(original, encoding="utf-8")


def _tool_render_screenshot(
    file_path: str,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    **_: Any,
) -> dict[str, Any]:
    """Render an HTML file headlessly via Playwright and return a Base64 PNG.

    Falls back gracefully to a structured stub when Playwright is unavailable so that
    the engine pipeline never blocks on a missing optional dependency.

    Security: path-traversal guarded; only .html/.htm files allowed.
    """
    resolved = _jail_path(file_path)
    if resolved.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(
            f"render_screenshot only supports .html/.htm files, got: '{resolved.suffix}'"
        )
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: '{file_path}'")

    try:
        # type: ignore[import-untyped]
        from playwright.sync_api import sync_playwright
        import base64

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(
                viewport={"width": int(viewport_width),
                          "height": int(viewport_height)}
            )
            page.goto(resolved.as_uri(),
                      wait_until="networkidle", timeout=10_000)
            png_bytes = page.screenshot(full_page=False)
            browser.close()

        b64 = base64.b64encode(png_bytes).decode("ascii")
        return {
            "file_path": str(resolved.relative_to(_WORKSPACE_ROOT)),
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "screenshot_b64": b64,
            "format": "png",
            "renderer": "playwright",
        }
    except ImportError:
        # Playwright not installed — return a structured placeholder so the
        # Art Director node can still produce a deterministic response.
        return {
            "file_path": str(resolved.relative_to(_WORKSPACE_ROOT)),
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "screenshot_b64": None,
            "format": "png",
            "renderer": "stub",
            "message": (
                "Playwright is not installed. Install with: "
                "pip install playwright && playwright install chromium"
            ),
        }
    except Exception as exc:
        return {
            "file_path": str(resolved.relative_to(_WORKSPACE_ROOT)),
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "screenshot_b64": None,
            "format": "png",
            "renderer": "error",
            "message": str(exc)[:200],
        }


# ── Tool registry ─────────────────────────────────────────────────────────────

_TOOL_REGISTRY: dict[str, tuple[Callable[..., dict[str, Any]], MCPToolSpec]] = {
    "file_read": (_tool_file_read, MCPToolSpec(
        uri=f"{_MCP_PREFIX}file_read",
        name="file_read",
        description="Read a file's text content from within the workspace.",
        parameters=[{
            "name": "path",
            "type": "string",
            "description": "Workspace-relative file path",
        }],
    )),
    "file_write": (_tool_file_write, MCPToolSpec(
        uri=f"{_MCP_PREFIX}file_write",
        name="file_write",
        description="Write text content to a workspace file (non-executable formats only).",
        parameters=[
            {"name": "path", "type": "string",
                "description": "Workspace-relative file path"},
            {"name": "content", "type": "string",
                "description": "UTF-8 text to write"},
        ],
    )),
    "code_analyze": (_tool_code_analyze, MCPToolSpec(
        uri=f"{_MCP_PREFIX}code_analyze",
        name="code_analyze",
        description=(
            "Statically analyse Python code: imports, error patterns, async usage, LOC, "
            "and an AST symbol_map with exact line ranges for every class, function, and method. "
            "Supply file_path (workspace-relative) to analyse a file directly, or pass raw code string."
        ),
        parameters=[
            {"name": "code", "type": "string",
                "description": "Python source code snippet to analyse (optional if file_path given)"},
            {"name": "file_path", "type": "string",
                "description": "Workspace-relative path to a Python file for symbol mapping"},
        ],
    )),
    "web_lookup": (_tool_web_lookup, MCPToolSpec(
        uri=f"{_MCP_PREFIX}web_lookup",
        name="web_lookup",
        description="Search the structured SOTA signal catalogue for best-practice patterns.",
        parameters=[{
            "name": "query",
            "type": "string",
            "description": "Query string (keyword or phrase)",
        }],
    )),
    "run_tests": (_tool_run_tests, MCPToolSpec(
        uri=f"{_MCP_PREFIX}run_tests",
        name="run_tests",
        description="Execute a pytest test file and return pass/fail verdict + output.",
        parameters=[{
            "name": "test_path",
            "type": "string",
            "description": "Path inside the tests/ directory",
        }],
    )),
    "run_tests_isolated": (_tool_run_tests_isolated, MCPToolSpec(
        uri=f"{_MCP_PREFIX}run_tests_isolated",
        name="run_tests_isolated",
        description=(
            "Sandbox crucible: patch a source file, run targeted tests, then atomically "
            "revert the file.  Enables ghost branches to race speculative patches with "
            "zero blast radius — the original is always restored in a finally block."
        ),
        parameters=[
            {"name": "file_path", "type": "string",
                "description": "Workspace-relative source file to patch"},
            {"name": "patch_search", "type": "string",
                "description": "Exact verbatim string to replace (≤30 lines)"},
            {"name": "patch_replace", "type": "string",
                "description": "Replacement string (the proposed fix)"},
            {"name": "test_path", "type": "string",
                "description": "Test file path inside tests/ to run after patching"},
            {"name": "timeout", "type": "integer",
                "description": "Subprocess timeout in seconds (default 60)"},
        ],
    )),
    "read_error": (_tool_read_error, MCPToolSpec(
        uri=f"{_MCP_PREFIX}read_error",
        name="read_error",
        description="Parse a Python traceback or error string into structured error data.",
        parameters=[{
            "name": "error_text",
            "type": "string",
            "description": "Traceback or error message string",
        }],
    )),
    "spawn_process": (_tool_spawn_process, MCPToolSpec(
        uri=f"{_MCP_PREFIX}spawn_process",
        name="spawn_process",
        description="Emit a validated BranchSpec-compatible payload for dynamic branching.",
        parameters=[
            {"name": "branch_type", "type": "string",
                "description": "fork | clone | share"},
            {"name": "intent", "type": "string",
                "description": "Child branch intent"},
            {"name": "mandate", "type": "string",
                "description": "Child branch mandate text"},
            {"name": "target", "type": "string",
                "description": "Optional file/service target"},
            {"name": "parent_branch_id", "type": "string",
                "description": "Optional parent branch id"},
        ],
    )),
    "patch_apply": (_tool_patch_apply, MCPToolSpec(
        uri=f"{_MCP_PREFIX}patch_apply",
        name="patch_apply",
        description=(
            "Surgical micro-patch: find search_block in a workspace file and replace it "
            "with replace_block.  Never rewrites the whole file — minimises blast radius."
        ),
        parameters=[
            {"name": "file_path", "type": "string",
                "description": "Workspace-relative path to the file"},
            {"name": "search_block", "type": "string",
                "description": "Exact text to locate (≤30 lines)"},
            {"name": "replace_block", "type": "string",
                "description": "Replacement text"},
            {"name": "fuzzy", "type": "boolean",
                "description": "If true, collapse whitespace during matching (default false)"},
        ],
    )),
    "render_screenshot": (_tool_render_screenshot, MCPToolSpec(
        uri=f"{_MCP_PREFIX}render_screenshot",
        name="render_screenshot",
        description=(
            "Render an HTML/component file headlessly via Playwright and return a "
            "Base64-encoded PNG screenshot for visual inspection or Art-Director evaluation."
        ),
        parameters=[
            {"name": "file_path", "type": "string",
                "description": "Workspace-relative path to an .html file"},
            {"name": "viewport_width", "type": "integer",
                "description": "Viewport width in pixels (default 1280)"},
            {"name": "viewport_height", "type": "integer",
                "description": "Viewport height in pixels (default 800)"},
        ],
    )),
}


# ── Manager ───────────────────────────────────────────────────────────────────


class MCPManager:
    """MCP tool discovery and dispatch.

    Usage::

        mcp = MCPManager()
        tools = mcp.manifest()                         # list[MCPToolSpec]
        result = mcp.call("file_read", path="engine/config.py")
        result2 = mcp.call_uri("mcp://tooloo/web_lookup", query="async python")
    """

    def manifest(self) -> list[MCPToolSpec]:
        """Return the full tool manifest (all registered tool specs)."""
        return [spec for _, spec in _TOOL_REGISTRY.values()]

    def call(self, tool_name: str, **kwargs: Any) -> MCPCallResult:
        """Invoke a registered MCP tool by short name, with kwargs as parameters."""
        if tool_name not in _TOOL_REGISTRY:
            return MCPCallResult(
                uri=f"{_MCP_PREFIX}{tool_name}",
                success=False,
                output=None,
                error=(
                    f"Tool '{tool_name}' is not registered. "
                    f"Available: {list(_TOOL_REGISTRY)}"
                ),
            )
        handler, spec = _TOOL_REGISTRY[tool_name]
        try:
            output = handler(**kwargs)
            return MCPCallResult(uri=spec.uri, success=True, output=output)
        except Exception as exc:
            return MCPCallResult(
                uri=spec.uri,
                success=False,
                output=None,
                error=str(exc),
            )

    def call_uri(self, uri: str, **kwargs: Any) -> MCPCallResult:
        """Invoke a tool by its full MCP URI (e.g. ``mcp://tooloo/file_read``)."""
        if not uri.startswith(_MCP_PREFIX):
            return MCPCallResult(
                uri=uri,
                success=False,
                output=None,
                error=f"Unknown URI scheme: '{uri}'",
            )
        tool_name = uri[len(_MCP_PREFIX):]
        return self.call(tool_name, **kwargs)
