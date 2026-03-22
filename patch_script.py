import re

with open("engine/self_improvement.py", "r") as f:
    text = f.read()

# I want to add `_implement_top_assessments` inside SelfImprovementEngine
# and call it in `run()`

fn_text = """
    def _implement_top_assessments(
        self, assessments: list[ComponentAssessment], improvement_id: str
    ) -> None:
        \"\"\"Autonomously implement the highest value SOTA suggestions using NStroke.\"\"\"
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return

        valid_assessments = [
            a for a in assessments 
            if a.execution_success and a.suggestions and "retry" not in a.suggestions[0].lower()
        ]
        top_assessments = sorted(valid_assessments, key=lambda a: a.value_score, reverse=True)[:2]

        for assessment in top_assessments:
            component_name = assessment.component
            suggestions_text = "\\n".join(f"- {s}" for s in assessment.suggestions)
            file_path = _COMPONENT_SOURCE.get(component_name)
            if not file_path:
                continue

            mandate_text = (
                f"Carefully implement these specific 2026 SOTA improvements on '{file_path}':\\n"
                f"{suggestions_text}\\n\\n"
                "1. Use `file_read` to inspect current file.\\n"
                "2. Apply these exact improvements using `patch_apply` tool ONLY. "
                "Ensure syntax is perfect and imports are updated.\\n"
                "3. Run `run_tests` to verify no regressions.\\n"
                "4. If tests fail, heal the code and repeat until tests pass.\\n"
                "Leave the file functionally solid and strictly correct."
            )

            # ── Dynamic MetaArchitect DAG generation ───────────────
            topology_proof = self._meta_architect.generate(
                mandate_text, intent="BUILD"
            )

            # ── Formulate LockedIntent ─────────────────────────────
            from engine.router import LockedIntent
            from datetime import datetime, UTC
            locked_intent = LockedIntent(
                intent="BUILD",
                confidence=topology_proof.confidence_proof.proof_confidence,
                value_statement=f"Implement SOTA fixes for {component_name}",
                constraint_summary="Must pass all tests and compile perfectly.",
                mandate_text=mandate_text,
                context_turns=[],
                locked_at=datetime.now(UTC).isoformat(),
            )

            # ── Execute NStroke ────────────────────────────────────
            # Try/except to ensure one failure doesn't halt the next
            try:
                self._get_n_stroke().run(
                    locked_intent=locked_intent,
                    pipeline_id=f"impl-{improvement_id}-{component_name}",
                )
            except Exception as e:
                pass
"""

# Now insert `_implement_top_assessments` after `_run_fluid_crucible`
target_insert = "    def _get_n_stroke(self) -> NStrokeEngine:"
replaced_text = text.replace(target_insert, fn_text + "\n" + target_insert)

# Now call it in `run()`
run_target = """        # ── Phase 2: Regression Gate ─────────────────────────────────────────
        if run_regression_gate:
            regression_passed, regression_details = self._run_regression_gate(
                improvement_id
            )
        else:
            regression_passed, regression_details = True, "skipped by caller\""""

run_replace = """        # ── Phase 1.5: Autonomous Implementation ──────────────────────────────
        if run_regression_gate:
            self._implement_top_assessments(assessments, improvement_id)

        # ── Phase 2: Regression Gate ─────────────────────────────────────────
        if run_regression_gate:
            regression_passed, regression_details = self._run_regression_gate(
                improvement_id
            )
        else:
            regression_passed, regression_details = True, "skipped by caller\""""

replaced_text = replaced_text.replace(run_target, run_replace)

async_run_target = """        # Phase 2: Regression Gate
        if run_regression_gate:
            regression_passed, regression_details = self._run_regression_gate(
                improvement_id
            )
        else:
            regression_passed, regression_details = True, "skipped by caller\""""

async_run_replace = """        # Phase 1.5: Autonomous Implementation
        if run_regression_gate:
            self._implement_top_assessments(assessments, improvement_id)

        # Phase 2: Regression Gate
        if run_regression_gate:
            regression_passed, regression_details = self._run_regression_gate(
                improvement_id
            )
        else:
            regression_passed, regression_details = True, "skipped by caller\""""

replaced_text = replaced_text.replace(async_run_target, async_run_replace)

if replaced_text != text:
    with open("engine/self_improvement.py", "w") as f:
        f.write(replaced_text)
    print("Patched successfully")
else:
    print("Could not find targets")
