"""Tests for walk-forward evaluation.

The point of separating this from validation.py is that these folds actually
hold data back. The tests below are mostly about that boundary: that no
out-of-sample bar was ever in a training window, that the embargo separates
them, and that the stitched path covers each bar exactly once.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backtest.walkforward import (
    Fold,
    WalkForwardError,
    _oos_returns,
    make_folds,
    walk_forward,
)


def _dates(n: int = 1200) -> pd.DatetimeIndex:
    return pd.bdate_range("2020-01-01", periods=n)


class TestMakeFolds:
    def test_test_windows_never_overlap(self) -> None:
        folds = make_folds(_dates(), n_folds=5, embargo_bars=5)
        for earlier, later in zip(folds, folds[1:]):
            assert earlier.test_end < later.test_start

    def test_test_windows_leave_no_gap(self) -> None:
        """A gap would silently drop bars from the stitched path."""
        index = _dates()
        folds = make_folds(index, n_folds=5, embargo_bars=5)
        for earlier, later in zip(folds, folds[1:]):
            after_earlier = index[index.get_loc(earlier.test_end) + 1]
            assert after_earlier == later.test_start

    def test_no_training_bar_is_ever_an_out_of_sample_bar(self) -> None:
        for fold in make_folds(_dates(), n_folds=5, embargo_bars=5):
            assert fold.train_end < fold.test_start

    def test_the_embargo_actually_separates_the_windows(self) -> None:
        index = _dates()
        embargo = 7
        for fold in make_folds(index, n_folds=4, embargo_bars=embargo):
            gap = index.get_loc(fold.test_start) - index.get_loc(fold.train_end)
            assert gap == embargo + 1

    def test_without_an_embargo_the_windows_touch(self) -> None:
        index = _dates()
        for fold in make_folds(index, n_folds=4, embargo_bars=0):
            assert index.get_loc(fold.test_start) - index.get_loc(fold.train_end) == 1

    def test_anchored_folds_grow_from_one_start(self) -> None:
        folds = make_folds(_dates(), n_folds=5, anchored=True)
        assert len({fold.train_start for fold in folds}) == 1
        lengths = [fold.train_end - fold.train_start for fold in folds]
        assert lengths == sorted(lengths)

    def test_rolling_folds_move_their_start_forward(self) -> None:
        folds = make_folds(_dates(), n_folds=5)
        starts = [fold.train_start for fold in folds]
        assert starts == sorted(starts)
        assert len(set(starts)) == len(starts)

    def test_an_explicit_train_length_is_honoured(self) -> None:
        index = _dates()
        folds = make_folds(index, n_folds=4, train_bars=100, embargo_bars=3)
        for fold in folds:
            span = index.get_loc(fold.train_end) - index.get_loc(fold.train_start) + 1
            assert span == 100

    def test_one_fold_is_not_a_walk_forward(self) -> None:
        with pytest.raises(WalkForwardError, match="at least 2 folds"):
            make_folds(_dates(), n_folds=1)

    def test_unsorted_dates_are_refused_rather_than_sorted_silently(self) -> None:
        index = _dates(50)[::-1]
        with pytest.raises(WalkForwardError, match="sorted ascending"):
            make_folds(index, n_folds=3)

    def test_too_few_bars_to_fold(self) -> None:
        with pytest.raises(WalkForwardError, match="cannot make 5 test windows"):
            make_folds(_dates(4), n_folds=5)

    def test_an_embargo_that_eats_the_training_window_is_refused(self) -> None:
        with pytest.raises(WalkForwardError, match="no training window"):
            make_folds(_dates(60), n_folds=5, embargo_bars=40)

    def test_a_negative_embargo_is_refused(self) -> None:
        with pytest.raises(WalkForwardError, match="cannot be negative"):
            make_folds(_dates(), n_folds=3, embargo_bars=-1)


class _StubEngine:
    """Writes the equity artifact the real engine writes, and nothing else.

    It takes a config in its constructor because the real engines do -- which
    a stub with a bare __init__ would have hidden until the default factory
    was used for real. It writes ``benchmark_equity`` for the same reason: the
    real engine's equity.csv carries it, and a stub omitting it would let the
    stitched benchmark look untestable when it is merely unwritten.
    """

    seen_configs: list[dict] = []

    def __init__(self, config: dict) -> None:
        self.config = config

    def run_backtest(self, config, loader, signal_engine, run_dir, bars_per_year=252):
        _StubEngine.seen_configs.append(dict(config))
        index = pd.bdate_range(config["start_date"], config["end_date"])
        rng = np.random.default_rng(len(index))
        equity = pd.Series(np.cumprod(1 + rng.normal(0.0004, 0.01, len(index))) * 1e6, index=index)
        bench = pd.Series(np.cumprod(1 + rng.normal(0.0002, 0.009, len(index))) * 1e6, index=index)
        artifacts = Path(run_dir) / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame({"equity": equity, "benchmark_equity": bench})
        frame.index.name = "timestamp"
        frame.to_csv(artifacts / "equity.csv")
        return {"sharpe": 1.0}


class _ExitingEngine:
    def __init__(self, config: dict) -> None:
        self.config = config

    def run_backtest(self, *args, **kwargs):
        raise SystemExit(1)


class _EmptyArtifactEngine:
    def __init__(self, config: dict) -> None:
        self.config = config

    def run_backtest(self, config, loader, signal_engine, run_dir, bars_per_year=252):
        (Path(run_dir) / "artifacts").mkdir(parents=True, exist_ok=True)
        return {"sharpe": 0.0}


class TestWalkForwardRun:
    def _run(self, tmp_path, **kwargs):
        _StubEngine.seen_configs = []
        config = {"codes": ["VRE.VN"], "initial_cash": 1_000_000}
        return walk_forward(
            config,
            loader=object(),
            signal_engine_factory=lambda cfg: object(),
            run_dir=tmp_path,
            dates=_dates(),
            engine_factory=_StubEngine,
            **kwargs,
        )

    def test_each_fold_gets_its_own_directory_and_artifacts(self, tmp_path: Path) -> None:
        self._run(tmp_path, n_folds=4)
        for i in range(4):
            assert (tmp_path / f"fold_{i:02d}" / "artifacts" / "equity.csv").exists()

    def test_the_stitched_path_covers_each_bar_exactly_once(self, tmp_path: Path) -> None:
        out = self._run(tmp_path, n_folds=5, embargo_bars=5)
        equity = out["oos_equity"]
        assert not equity.index.has_duplicates
        assert out["oos_bars"] == len(equity)
        assert equity.index.is_monotonic_increasing

    def test_the_stitched_path_starts_at_the_first_test_bar(self, tmp_path: Path) -> None:
        out = self._run(tmp_path, n_folds=5, embargo_bars=5)
        folds = make_folds(_dates(), n_folds=5, embargo_bars=5)
        assert out["oos_equity"].index[0] == folds[0].test_start
        assert out["oos_equity"].index[-1] == folds[-1].test_end

    def test_no_training_bar_reaches_the_stitched_path(self, tmp_path: Path) -> None:
        """The property the whole module exists for."""
        out = self._run(tmp_path, n_folds=5, embargo_bars=5)
        folds = make_folds(_dates(), n_folds=5, embargo_bars=5)
        for stamp in out["oos_equity"].index:
            owning = [f for f in folds if f.test_start <= stamp <= f.test_end]
            assert len(owning) == 1
            assert stamp > owning[0].train_end

    def test_every_fold_is_told_where_its_training_data_stops(self, tmp_path: Path) -> None:
        """The module cannot enforce the boundary, so it must at least hand it over."""
        self._run(tmp_path, n_folds=4, embargo_bars=5)
        assert len(_StubEngine.seen_configs) == 4
        for config in _StubEngine.seen_configs:
            assert config["train_end"] < config["oos_start"] <= config["end_date"]
            assert config["start_date"] <= config["train_end"]

    def test_each_fold_says_in_its_run_card_what_was_held_back(self, tmp_path: Path) -> None:
        self._run(tmp_path, n_folds=3)
        for config in _StubEngine.seen_configs:
            assert any("WALK-FORWARD FOLD" in w for w in config["_run_card_warnings"])

    def test_a_fresh_signal_engine_is_built_for_every_fold(self, tmp_path: Path) -> None:
        """A stateful engine must not carry fold 2's fit into fold 3."""
        built: list[object] = []

        def factory(config):
            instance = object()
            built.append((instance, config.get("train_end")))
            return instance

        _StubEngine.seen_configs = []
        walk_forward(
            {"codes": ["VRE.VN"]},
            loader=object(),
            signal_engine_factory=factory,
            run_dir=tmp_path,
            dates=_dates(),
            n_folds=4,
            engine_factory=_StubEngine,
        )
        assert len(built) == 4
        assert len({id(instance) for instance, _ in built}) == 4
        # And each was told where its own training window stops -- the channel
        # BaseEngine does not provide, so without it a fitting engine could not
        # have honoured the boundary this module requires of it.
        boundaries = [train_end for _, train_end in built]
        assert all(boundaries) and boundaries == sorted(boundaries)

    def test_the_summary_is_written_where_a_reader_will_find_it(self, tmp_path: Path) -> None:
        out = self._run(tmp_path, n_folds=3)
        assert (tmp_path / "walk_forward.json").exists()
        assert (tmp_path / "oos_equity.csv").exists()
        assert len(out["folds"]) == 3

    def test_the_out_of_sample_metrics_clear_the_configured_hurdle(self, tmp_path: Path) -> None:
        _StubEngine.seen_configs = []
        plain = walk_forward(
            {"codes": ["X"], "initial_cash": 1_000_000},
            object(), lambda cfg: object(), tmp_path / "a",
            dates=_dates(), n_folds=3, engine_factory=_StubEngine,
        )
        _StubEngine.seen_configs = []
        hurdled = walk_forward(
            {"codes": ["X"], "initial_cash": 1_000_000, "risk_free": 0.05},
            object(), lambda cfg: object(), tmp_path / "b",
            dates=_dates(), n_folds=3, engine_factory=_StubEngine,
        )
        assert hurdled["oos_metrics"]["sharpe"] < plain["oos_metrics"]["sharpe"]

    def test_a_fold_that_kills_the_engine_names_itself(self, tmp_path: Path) -> None:
        """The engine calls sys.exit; a loop that swallowed that would hang silently."""
        with pytest.raises(WalkForwardError, match="fold 0.*stopped the engine"):
            walk_forward(
                {"codes": ["X"]}, object(), lambda cfg: object(), tmp_path,
                dates=_dates(), n_folds=3, engine_factory=_ExitingEngine,
            )

    def test_a_fold_with_no_equity_curve_is_not_quietly_skipped(self, tmp_path: Path) -> None:
        """A walk-forward with a hole in it is not a walk-forward."""
        with pytest.raises(WalkForwardError, match="produced no equity curve"):
            walk_forward(
                {"codes": ["X"]}, object(), lambda cfg: object(), tmp_path,
                dates=_dates(), n_folds=3, engine_factory=_EmptyArtifactEngine,
            )


class TestTheStitchedBenchmark:
    """A zero benchmark is not a benchmark.

    calc_metrics compares against a flat zero when given nothing, and reports
    information_ratio 0.0 -- which a reader takes as a measured absence of
    edge, not as an absent measurement.
    """

    def test_the_benchmark_is_stitched_when_every_fold_recorded_one(
        self, tmp_path: Path
    ) -> None:
        _StubEngine.seen_configs = []
        out = walk_forward(
            {"codes": ["VRE.VN"], "initial_cash": 1_000_000},
            loader=object(),
            signal_engine_factory=lambda cfg: object(),
            run_dir=tmp_path,
            dates=_dates(),
            n_folds=3,
            engine_factory=_StubEngine,
        )
        assert "information_ratio" in out["oos_metrics"]
        assert "benchmark_return" in out["oos_metrics"]

    def test_a_missing_benchmark_drops_the_field_rather_than_zeroing_it(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        original = _StubEngine.run_backtest

        def without_benchmark(self, config, loader, signal_engine, run_dir, **kwargs):
            metrics = original(self, config, loader, signal_engine, run_dir, **kwargs)
            path = run_dir / "artifacts" / "equity.csv"
            frame = pd.read_csv(path, index_col=0, parse_dates=True)
            frame.drop(columns=["benchmark_equity"], errors="ignore").to_csv(path)
            return metrics

        monkeypatch.setattr(_StubEngine, "run_backtest", without_benchmark)
        _StubEngine.seen_configs = []
        out = walk_forward(
            {"codes": ["VRE.VN"], "initial_cash": 1_000_000},
            loader=object(),
            signal_engine_factory=lambda cfg: object(),
            run_dir=tmp_path,
            dates=_dates(),
            n_folds=3,
            engine_factory=_StubEngine,
        )
        assert "information_ratio" not in out["oos_metrics"]
        assert "excess_return" not in out["oos_metrics"]
        assert "sharpe" in out["oos_metrics"]


class TestOutOfSampleSlicing:
    def _fold(self) -> Fold:
        return Fold(
            index=0,
            train_start=pd.Timestamp("2020-01-01"),
            train_end=pd.Timestamp("2020-01-10"),
            test_start=pd.Timestamp("2020-01-13"),
            test_end=pd.Timestamp("2020-01-17"),
        )

    def _write(self, tmp_path: Path) -> Path:
        index = pd.bdate_range("2020-01-01", "2020-01-17")
        equity = pd.Series(np.linspace(1_000_000, 1_100_000, len(index)), index=index)
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame({"equity": equity})
        frame.index.name = "timestamp"
        frame.to_csv(artifacts / "equity.csv")
        return tmp_path

    def test_only_test_window_bars_survive(self, tmp_path: Path) -> None:
        oos, _ = _oos_returns(self._write(tmp_path), self._fold())
        assert oos.index.min() == pd.Timestamp("2020-01-13")
        assert oos.index.max() == pd.Timestamp("2020-01-17")

    def test_the_first_test_bar_keeps_the_move_that_carried_into_it(self, tmp_path: Path) -> None:
        """Differencing after slicing would zero this bar and understate the path."""
        oos, _ = _oos_returns(self._write(tmp_path), self._fold())
        assert oos.iloc[0] != 0.0


class TestTheEngineContract:
    """The default factory has to match what the real engines actually accept."""

    def test_the_real_vn_engine_can_be_built_the_way_this_module_builds_it(self) -> None:
        from backtest.engines.vn_equity import VNEquityEngine

        engine = VNEquityEngine({"initial_cash": 1_000_000, "codes": ["VRE.VN"]})
        assert engine.initial_capital == 1_000_000

    def test_a_factory_taking_no_config_is_a_type_error_not_a_silent_pass(self) -> None:
        """This is the bug the stub hid: engines take a config, factories must pass it."""
        with pytest.raises(TypeError):
            _StubEngine()  # type: ignore[call-arg]
