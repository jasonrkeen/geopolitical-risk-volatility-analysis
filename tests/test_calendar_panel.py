from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from calendar_panel import LAG_COLUMNS, prepare_monthly_panel

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("october_present", [True, False])
def test_lags_use_previous_calendar_month(october_present: bool) -> None:
    dates = pd.date_range("2024-09-30", "2025-11-30", freq="ME")
    monthly = pd.DataFrame({"date": dates, "cpi": 100.0})
    for i, name in enumerate(LAG_COLUMNS):
        monthly[name] = np.arange(len(dates)) + 10 * i
    october = pd.Timestamp("2025-10-31")
    monthly.loc[monthly.date == october, "cpi"] = np.nan
    if not october_present:
        monthly = monthly.loc[monthly.date != october]
    panel = prepare_monthly_panel(monthly).set_index("date")
    assert panel.loc[october, ["cpi", "inflation_rate"]].isna().all()
    for name in LAG_COLUMNS:
        lag = panel.loc["2025-11-30", f"{name}_lag1"]
        if october_present:
            assert lag == monthly.set_index("date").loc[october, name]
        else:
            assert pd.isna(lag)


def test_published_panel_and_shared_holdout() -> None:
    panel = pd.read_csv(ROOT / "data_clean/merged_monthly_data.csv", index_col="date")
    assert panel.loc["2025-10-31", ["cpi", "inflation_rate"]].isna().all()
    for name in LAG_COLUMNS:
        assert panel.loc["2025-11-30", f"{name}_lag1"] == panel.loc["2025-10-31", name]
    forecasts = pd.read_csv(ROOT / "outputs/forecast_backtest_results.csv", index_col="date")
    expected = pd.date_range("2023-01-31", "2025-12-31", freq="ME").strftime("%Y-%m-%d")
    assert forecasts.index.tolist() == [date for date in expected if date != "2025-10-31"]
    for model in ("baseline", "controls", "enhanced"):
        prediction = forecasts[f"{model}_predicted_vix"]
        assert prediction.notna().all()
        np.testing.assert_allclose(forecasts.vix - prediction, forecasts[f"{model}_error"])
