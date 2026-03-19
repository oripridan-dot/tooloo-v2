from __future__ import annotations

from benchmark_metrics import run_benchmark
from engine.sandbox import DimensionScorer


class TestDimensionScorer:
    def test_scores_expected_dimensions(self) -> None:
        scorer = DimensionScorer()
        scores = scorer.score(
            original_conf=0.7,
            boosted_conf=0.9,
            tribunal_passed=True,
            refinement_verdict="pass",
            exec_success_rate=1.0,
        )
        names = {score.name for score in scores}
        assert {"efficiency", "quality", "accuracy"}.issubset(names)


class TestBenchmarkMetrics:
    def test_run_benchmark_shape(self) -> None:
        report = run_benchmark("efficiency,quality,accuracy,speed")
        assert report.aggregate.component_count == 17
        assert len(report.components) == 17
        assert report.aggregate.executor_p50_ms >= 0.0
        assert report.aggregate.executor_p90_ms >= 0.0
        assert report.aggregate.refinement_p50_ms >= 0.0
        assert report.aggregate.refinement_p90_ms >= 0.0

    def test_benchmark_component_metrics_are_bounded(self) -> None:
        report = run_benchmark("balanced")
        for component in report.components:
            assert 0.0 <= component.efficiency <= 1.0
            assert 0.0 <= component.quality <= 1.0
            assert 0.0 <= component.accuracy <= 1.0
            assert component.speed_ms >= 0.0
