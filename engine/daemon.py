import asyncio
import json
import re
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from engine.calibration_engine import CalibrationEngine
from engine.psyche_bank import PsycheBank
from engine.self_improvement import SelfImprovementEngine

# Re-calibration interval (Ebbinghaus half-life rule: every 7 days)
_RECAL_INTERVAL = timedelta(days=7)
_RECAL_STAMP_FILE = Path(__file__).resolve(
).parents[1] / "psyche_bank" / "last_recalibration.json"

# ── Repo root (used for path-jail checks) ─────────────────────────────────────
_REPO_ROOT: Path = Path(__file__).resolve().parents[1]

# ── Gemini client (initialised once at import time) ───────────────────────────
_gemini_client = None
_gemini_model = "gemini-2.5-flash"
try:
    from engine.config import GEMINI_API_KEY, GEMINI_MODEL as _cfg_model
    _gemini_model = _cfg_model or _gemini_model
    if GEMINI_API_KEY:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
except Exception:
    pass

# Core security files — changes require explicit user approval (Law 20)
_HIGH_RISK_COMPONENTS = {"tribunal", "psyche_bank", "router"}

# Control: configurable thresholds for daemon safety
_MAX_CYCLE_RETRIES = 3         # per-cycle retry ceiling before rollback
_DAEMON_CIRCUIT_BREAKER = 5    # consecutive failures before daemon pauses


class BackgroundDaemon:
    def __init__(self, broadcast_fn):
        self.active = False
        self._broadcast = broadcast_fn
        self.si_engine = SelfImprovementEngine()
        self._bank = PsycheBank()
        self._cal_engine = CalibrationEngine()
        self.awaiting_approval: list[dict[str, Any]] = []

    async def start(self):
        self.active = True
        self._broadcast({"type": "daemon_status", "status": "started"})
        # Law 17: isolate daemon loop as a managed asyncio task so the
        # FastAPI lifespan is not blocked and cancellation is clean.
        self._daemon_task = asyncio.create_task(self._run_daemon_loop())
        await self._daemon_task

    async def _run_daemon_loop(self) -> None:
        """Isolated daemon loop — can be cancelled without affecting the event loop."""
        while self.active:
            await self._cycle()
            await asyncio.sleep(60)

    def stop(self):
        self.active = False
        self._broadcast({"type": "daemon_status", "status": "stopped"})

    async def _cycle(self):
        # Prune expired tribunal rules before each scan to keep the bank lean.
        removed = self._bank.purge_expired()
        if removed:
            self._broadcast({"type": "daemon_rt",
                             "msg": f"PsycheBank: purged {removed} expired rule(s)"})
        # 7-day auto-recalibration (Ebbinghaus rule)
        await self._maybe_recalibrate()
        self._broadcast(
            {"type": "daemon_rt", "msg": "Initiating background scan..."})
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, self.si_engine.run)

        for a in report.assessments:
            for sugg in getattr(a, "suggestions", []):
                # Only act on FIX-format suggestions that target a real file
                if not re.match(r"FIX\s+\d+:\s*[\w/\.\-]+\.py:\d+", sugg):
                    continue

                is_high_risk = a.component in _HIGH_RISK_COMPONENTS
                assessment = self._score_proposal(
                    a.component, sugg, is_high_risk)
                proposal_id = str(uuid.uuid4())[:8]
                proposal = {
                    "id": proposal_id,
                    "component": a.component,
                    "suggestion": sugg,
                    "risk": assessment["risk"],
                    "roi": assessment["roi"],
                    "rationale": assessment["rationale"],
                    "status": "queued",
                }

                self._broadcast({"type": "daemon_rt",
                                 "msg": f"[{a.component}] Proposal {proposal_id}: "
                                         f"{proposal['risk']} risk · {proposal['roi']} ROI"})

                if is_high_risk:
                    proposal["status"] = "awaiting_approval"
                    self.awaiting_approval.append(proposal)
                    self._broadcast(
                        {"type": "daemon_approval_needed", "proposal": proposal})
                else:
                    await self._auto_execute(proposal)

    def _score_proposal(self, component: str, suggestion: str, is_high_risk: bool) -> dict[str, str]:
        """Evaluate proposal risk and ROI using Gemini when available."""
        fallback = {
            "risk": "High" if is_high_risk else "Medium",
            "roi": "High" if any(k in suggestion.lower() for k in ("latency", "executor", "router", "security")) else "Medium",
            "rationale": "Heuristic fallback used because the local evaluator was unavailable.",
        }
        if _gemini_client is None:
            return fallback

        prompt = (
            "You are Buddy, TooLoo's local ROI/risk gate. Return JSON only with keys "
            "risk, roi, rationale. risk/roi must be one of High, Medium, Low.\n"
            f"Component: {component}\n"
            f"High-risk component: {is_high_risk}\n"
            f"Suggestion: {suggestion[:600]}\n"
            "Score whether this autonomous patch is worth prioritising in the background."
        )
        try:
            resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                model=_gemini_model,
                contents=prompt,
            )
            payload = json.loads((resp.text or "{}").strip())
            risk = str(payload.get("risk", fallback["risk"])).title()
            roi = str(payload.get("roi", fallback["roi"])).title()
            if risk not in {"High", "Medium", "Low"}:
                risk = fallback["risk"]
            if roi not in {"High", "Medium", "Low"}:
                roi = fallback["roi"]
            return {
                "risk": "High" if is_high_risk else risk,
                "roi": roi,
                "rationale": str(payload.get("rationale", fallback["rationale"]))[:240],
            }
        except Exception:
            return fallback

    # ── Execution ─────────────────────────────────────────────────────────────

    async def _auto_execute(self, proposal: dict):
        """Generate a real code patch via Gemini, test it, and commit if green."""
        comp = proposal["component"]
        pid = proposal["id"]
        self._broadcast(
            {"type": "daemon_rt", "msg": f"[{comp}] Generating patch {pid}..."})

        loop = asyncio.get_event_loop()
        patch = await loop.run_in_executor(None, self._generate_patch, proposal)

        if patch is None:
            self._broadcast({"type": "daemon_rt",
                             "msg": f"[{comp}] Could not generate a valid patch — skipping {pid}"})
            proposal["status"] = "skipped"
            return

        file_rel, old_code, new_code = patch

        # Path-jail: must stay inside repo root
        full_path = (_REPO_ROOT / file_rel).resolve()
        if not str(full_path).startswith(str(_REPO_ROOT)):
            self._broadcast({"type": "daemon_rt",
                             "msg": f"[{comp}] Path traversal blocked: {file_rel}"})
            proposal["status"] = "skipped"
            return

        if not full_path.exists():
            self._broadcast({"type": "daemon_rt",
                             "msg": f"[{comp}] File not found: {file_rel}"})
            proposal["status"] = "skipped"
            return

        original = full_path.read_text(encoding="utf-8")
        if old_code not in original:
            self._broadcast({"type": "daemon_rt",
                             "msg": f"[{comp}] Code anchor not found in {file_rel} — skipping"})
            proposal["status"] = "skipped"
            return

        # Apply patch
        patched = original.replace(old_code, new_code, 1)
        full_path.write_text(patched, encoding="utf-8")
        self._broadcast({"type": "daemon_rt",
                         "msg": f"[{comp}] Patch applied to {file_rel} — running tests..."})

        # Run test suite
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-x", "-q",
             "--timeout=30", "--tb=no", "--no-header"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )

        if result.returncode == 0:
            summary_lines = [
                l for l in result.stdout.splitlines() if l.strip()]
            summary = summary_lines[-1] if summary_lines else "passed"
            self._broadcast({"type": "daemon_rt",
                             "msg": f"[{comp}] Tests ✓ {summary} — committing..."})
            subprocess.run(["git", "add", file_rel],
                           capture_output=True, cwd=str(_REPO_ROOT))
            git_msg = f"daemon: {proposal['suggestion'][:80]}"
            subprocess.run(["git", "commit", "-m", git_msg],
                           capture_output=True, cwd=str(_REPO_ROOT))
            proposal["status"] = "merged"
            self._broadcast({"type": "daemon_rt",
                             "msg": f"[{comp}] ✓ Real change committed to {file_rel}"})
        else:
            full_path.write_text(original, encoding="utf-8")  # revert
            err_lines = [l for l in result.stdout.splitlines()
                         if "FAILED" in l or "ERROR" in l]
            err_summary = "; ".join(err_lines[:2]) or "tests failed"
            self._broadcast({"type": "daemon_rt",
                             "msg": f"[{comp}] Tests ✗ ({err_summary}) — reverted {file_rel}"})
            proposal["status"] = "reverted"

    # ── Patch generation ──────────────────────────────────────────────────────

    def _generate_patch(self, proposal: dict) -> tuple[str, str, str] | None:
        """Ask Gemini to produce an old→new code replacement for the suggestion.

        Returns (file_rel_path, old_code, new_code) or None if generation fails.
        This method only reads files — all writes are done by the caller.
        """
        sugg = proposal["suggestion"]

        # Parse: "FIX N: engine/path.py:LINE — description"
        fix_m = re.match(
            r"FIX\s+\d+:\s*([\w/\.\-]+\.py):(\d+)\s*[—\-]+\s*(.+)", sugg)
        if not fix_m:
            return None

        file_rel = fix_m.group(1).strip()
        line_hint = int(fix_m.group(2))
        description = fix_m.group(3).strip()

        # Extract CODE snippet embedded in the suggestion string (if any)
        code_lines: list[str] = []
        in_code = False
        for line in sugg.splitlines():
            if line.strip().startswith("CODE:"):
                in_code = True
                rest = line.strip()[5:].strip()
                if rest:
                    code_lines.append(rest)
            elif in_code:
                code_lines.append(line)
        code_snippet = "\n".join(code_lines).strip()

        # Read file context around the line hint
        full_path = (_REPO_ROOT / file_rel).resolve()
        if not str(full_path).startswith(str(_REPO_ROOT)) or not full_path.exists():
            return None

        file_lines = full_path.read_text(encoding="utf-8").splitlines()
        ctx_start = max(0, line_hint - 20)
        ctx_end = min(len(file_lines), line_hint + 20)
        context = "\n".join(file_lines[ctx_start:ctx_end])

        if _gemini_client is None:
            return None

        snippet_block = (
            f"Suggested replacement snippet:\n```python\n{code_snippet}\n```\n\n"
            if code_snippet else ""
        )
        prompt = (
            f"You are making a surgical improvement to a Python codebase.\n\n"
            f"File: {file_rel}\n"
            f"Change: {description}\n"
            f"{snippet_block}"
            f"Context (lines {ctx_start + 1}–{ctx_end}):\n"
            f"```python\n{context}\n```\n\n"
            "Output ONLY these two blocks, nothing else:\n"
            "<<<OLD>>>\n"
            "<exact lines to replace — must be an exact verbatim substring of the context above>\n"
            "<<<NEW>>>\n"
            "<improved replacement — same indentation, minimal diff>\n"
            "<<<END>>>\n\n"
            "Rules:\n"
            "- OLD must copy-paste exactly from the context (same whitespace/indentation)\n"
            "- Change only what is needed for the described improvement\n"
            "- Maximum 25 lines each\n"
            "- No backtick fences, no prose, no explanation"
        )

        try:
            resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                model=_gemini_model, contents=prompt
            )
            raw = (resp.text or "").strip()
        except Exception as e:
            self._broadcast(
                {"type": "daemon_rt", "msg": f"Gemini patch error: {e}"})
            return None

        old_m = re.search(r"<<<OLD>>>\n(.*?)\n<<<NEW>>>", raw, re.DOTALL)
        new_m = re.search(r"<<<NEW>>>\n(.*?)(?:\n<<<END>>>|$)", raw, re.DOTALL)
        if not old_m or not new_m:
            return None

        old_code = old_m.group(1)
        new_code = new_m.group(1)
        if not old_code.strip() or not new_code.strip():
            return None

        return file_rel, old_code, new_code

    # ── 7-day auto-recalibration ───────────────────────────────────────────────

    async def _maybe_recalibrate(self) -> None:
        """Run a 5-cycle CalibrationEngine pass if the last run was >7 days ago.

        The last-run timestamp is persisted in
        psyche_bank/last_recalibration.json so the interval survives process
        restarts.
        """
        now = datetime.now(timezone.utc)
        last_run: datetime | None = None

        if _RECAL_STAMP_FILE.exists():
            try:
                data = json.loads(
                    _RECAL_STAMP_FILE.read_text(encoding="utf-8"))
                last_run = datetime.fromisoformat(data.get("last_run", ""))
            except Exception:
                last_run = None

        if last_run is not None and (now - last_run) < _RECAL_INTERVAL:
            return  # not yet due

        self._broadcast(
            {"type": "daemon_rt",
                "msg": "[CalibrationEngine] 7-day recalibration triggered…"}
        )
        loop = asyncio.get_event_loop()
        try:
            report = await loop.run_in_executor(None, self._cal_engine.run_5_cycles)
            # Persist calibration artefacts (proof.json, rules.cog.json, etc.)
            self._cal_engine.persist(report)
            # Record the timestamp so we don't re-run for another 7 days
            _RECAL_STAMP_FILE.write_text(
                json.dumps({"last_run": now.isoformat(), "run_id": report.run_id},
                           indent=2),
                encoding="utf-8",
            )
            self._broadcast(
                {"type": "daemon_rt",
                 "msg": f"[CalibrationEngine] ✓ Recalibration complete "
                         f"(run={report.run_id}, "
                         f"alignment {report.system_alignment_before:.4f}"
                         f"→{report.system_alignment_after:.4f})"}
            )
        except Exception as exc:
            self._broadcast(
                {"type": "daemon_rt",
                 "msg": f"[CalibrationEngine] Recalibration failed: {exc}"}
            )

    # ── Approval flow ─────────────────────────────────────────────────────────

    def approve(self, proposal_id: str):
        for p in self.awaiting_approval:
            if p["id"] == proposal_id:
                p["status"] = "approved"
                self._broadcast({"type": "daemon_rt",
                                 "msg": f"User approved {proposal_id}. Handing off to execution."})
                asyncio.create_task(self._auto_execute(p))
                return {"status": "success"}
        return {"status": "not_found"}

    def reject(self, proposal_id: str):
        for p in self.awaiting_approval:
            if p["id"] == proposal_id:
                p["status"] = "rejected"
                self._broadcast({"type": "daemon_rt",
                                 "msg": f"User rejected {proposal_id} — discarded."})
                return {"status": "success"}
        return {"status": "not_found"}
