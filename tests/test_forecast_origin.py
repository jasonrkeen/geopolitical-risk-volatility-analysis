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
