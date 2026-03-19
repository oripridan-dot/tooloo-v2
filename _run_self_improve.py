#!/usr/bin/env python3
"""One-shot self-improvement cycle runner."""
from engine.self_improvement import SelfImprovementEngine, _COMPONENTS

W = 60
print("=" * W)
print("  TooLoo V2 — Self-Improvement Cycle")
print("  Scope: 8 nodes · 3 waves · max ×3 parallel · deep-parallel")
print("=" * W)

engine = SelfImprovementEngine()
report = engine.run()

# Component → wave lookup (ComponentAssessment has no wave field directly)
_wave_of = {c["component"]: c["wave"] for c in _COMPONENTS}
elapsed_s = report.latency_ms / 1000

print(f"\nRun ID  : {report.improvement_id}")
print(f"Time    : {report.ts}")
print(f"Elapsed : {elapsed_s:.2f}s")
print(f"Verdict : {report.refinement_verdict.upper()}")
print(f"Results : {report.components_assessed} components · {report.waves_executed} waves · "
      f"success={report.refinement_success_rate:.0%}")
print(f"Signals : {report.total_signals} JIT SOTA signals harvested\n")

wave_labels = {
    1: "Wave 1 [core-security]",
    2: "Wave 2 [performance]",
    3: "Wave 3 [meta-analysis]",
}

assessments_by_wave = sorted(
    report.assessments,
    key=lambda a: (_wave_of.get(a.component, 99), a.component),
)

current_wave = None
for a in assessments_by_wave:
    wave = _wave_of.get(a.component, 99)
    if wave != current_wave:
        current_wave = wave
        label = wave_labels.get(wave, f"Wave {wave}")
        print(f"──── {label} {'─'*(W - 6 - len(label))}")
    status = "✓ PASS" if (
        a.tribunal_passed and a.execution_success) else "✗ FAIL"
    print(f"  {status}  {a.component:<20}  intent={a.intent:<8}  "
          f"conf={a.original_confidence:.2f}→{a.boosted_confidence:.2f}  jit={a.jit_source}")
    for sig in a.jit_signals[:2]:
        print(f"           ↳ {sig[:76]}")
    for sug in (a.suggestions or [])[:1]:
        print(f"           → {sug[:76]}")
    print()

print(f"──── Top Recommendations {'─'*(W - 26)}")
for i, rec in enumerate(report.top_recommendations, 1):
    print(f"  {i}. {rec}")
print()
