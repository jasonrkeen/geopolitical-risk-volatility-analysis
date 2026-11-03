import numpy as np
import pandas as pd
import pytest

from research.forecast_origin import COUNTRIES, MODELS, Snapshot, features


def test_december_uses_only_released_cpi_and_prior_market_values() -> None:
    def series(values: list[float], dates: list[str]) -> pd.Series:
        return pd.Series(values, index=pd.to_datetime(dates))

    data = Snapshot({
        "VIXCLS": series([16., 18., 999.], ["2025-11-03", "2025-11-28", "2025-12-01"]),
        "DCOILBRENTEU": series([60., 66., 999.], ["2025-10-02", "2025-10-31", "2025-11-03"]),
        "FEDFUNDS": series([4., 999.], ["2025-10-01", "2025-11-01"]),
        "CPIAUCSL": series([100., 103., 999.], ["2024-09-01", "2025-09-01", "2025-11-01"]),
    }, pd.DataFrame({k: [2., 999.] for k in COUNTRIES.values()},
                    index=pd.period_range("2025-10", periods=2, freq="M")), [])
    row = features(pd.Period("2025-12", "M"), data)
    assert row["cpi_month"] == "2025-09"
    assert row["inflation"] == pytest.approx(3.)
    assert (row["vix"], row["brent"], row["fed"], row["gpr_usa"]) == (17., 63., 4., 2.)
    assert row["covid"] == row["war"] == 0


def test_published_forecasts_and_metrics() -> None:
    from research.forecast_origin import OUTPUT
    out = pd.read_csv(OUTPUT / "monthly.csv", index_col="target")
    scores = pd.read_csv(OUTPUT / "scores.csv", index_col="model")
    assert out.index.tolist() == list(pd.period_range("2023-01", "2025-12", freq="M").astype(str))
    assert out.loc["2025-10", "cpi_month"] == "2025-08"
    assert out.loc["2025-11", "cpi_month"] == out.loc["2025-12", "cpi_month"] == "2025-09"
    valid = out.exclusion.isna()
    assert out.index[~valid].tolist() == ["2025-11", "2025-12"]
    assert out.loc[~valid, "vix_calendar_difference"].tolist() == ["2025-10-31", "2025-11-28"]
    for name in MODELS:
        pred = out[name + "_prediction"]
        assert pred.notna().equals(valid)
        error = out.loc[valid, "actual"] - pred[valid]
        np.testing.assert_allclose(out.loc[valid, name + "_error"], error, atol=1e-12)
        np.testing.assert_allclose(scores.loc[name, ["mae", "rmse", "mape"]].astype(float),
                                   [error.abs().mean(), np.sqrt(error.pow(2).mean()),
                                    (100 * error.abs() / out.loc[valid, "actual"]).mean()])


def test_outcome_revisions_cannot_change_cutoffs_or_forecasts(tmp_path, monkeypatch) -> None:
    from research import forecast_origin as study

    (tmp_path / "research").mkdir()
    (tmp_path / "data_clean").mkdir()
    (tmp_path / "data_raw").mkdir()
    monkeypatch.setattr(study, "ROOT", tmp_path)
    monkeypatch.setattr(study, "OUTPUT", tmp_path / "outputs")
    monkeypatch.setattr(study, "LAST_TARGET", pd.Period("2023-02", "M"))
    sessions = ["2022-12-29", "2022-12-30", "2023-01-30", "2023-01-31"]
    pd.DataFrame({"session_date": sessions}).to_csv(tmp_path / "research/vix_sessions.csv", index=False)
    months = pd.date_range("2009-01-01", "2023-01-01", freq="MS")
    series = pd.Series(np.arange(len(months), dtype=float) + 100, index=months)
    vix = pd.concat([series.loc[:"2022-11-01"], pd.Series(
        [19., 20., 21.], index=pd.to_datetime(sessions[:3]))])
    gpr = pd.DataFrame({key: series.values for key in study.COUNTRIES.values()},
                       index=months.to_period("M"))

    def archive(cutoff, cache, pins):
        fred = {"VIXCLS": vix, "FEDFUNDS": series, "DCOILBRENTEU": series, "CPIAUCSL": series}
        return Snapshot({key: values.loc[:cutoff] for key, values in fred.items()}, gpr,
                        [dict(cutoff=str(cutoff.date()), series="fixture", sha256="fixture")])

    monkeypatch.setattr(study, "snapshot", archive)
    outcome = tmp_path / "data_clean/merged_monthly_data.csv"
    outcome.write_text("date,vix\n2023-01-31,22\n2023-02-28,23\n")
    study.run(tmp_path)
    first = pd.read_csv(study.OUTPUT / "monthly.csv")
    # A revised outcome disappears and the later daily file omits both final sessions.
    outcome.write_text("date,vix\n2023-02-28,24\n")
    (tmp_path / "data_raw/vix.csv").write_text(
        "observation_date,VIXCLS\n2022-12-29,19\n2023-01-30,21\n")
    study.run(tmp_path)
    revised = pd.read_csv(study.OUTPUT / "monthly.csv")
    columns = ["cutoff", "exclusion", "vix_calendar_difference",
               *(name + "_prediction" for name in study.MODELS)]
    pd.testing.assert_frame_equal(first[columns], revised[columns])
    assert revised.cutoff.tolist() == [sessions[1], sessions[3]]
    assert pd.isna(revised.loc[0, "actual"]) and pd.notna(revised.loc[0, "baseline_prediction"])
    assert revised.loc[1, "vix_calendar_difference"] == sessions[3]
