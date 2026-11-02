"""Monthly transformations for the 2010-2025 study window."""
import pandas as pd

STUDY_START = "2010-01-31"
STUDY_END = "2025-12-31"
LAG_COLUMNS = ("vix", "gpr_usa", "gpr_china", "gpr_russia")


def prepare_monthly_panel(monthly: pd.DataFrame) -> pd.DataFrame:
    """Keep missing months explicit and build lags before model exclusions."""
    dates = pd.date_range(STUDY_START, STUDY_END, freq="ME", name="date")
    panel = monthly.set_index("date").reindex(dates)
    panel["inflation_rate"] = panel["cpi"].div(panel["cpi"].shift(12)).sub(1).mul(100)
    # Preserve the original 2010 CPI warm-up and first eligible lagged outcome.
    panel = panel.iloc[12:].copy()
    for column in LAG_COLUMNS:
        panel[f"{column}_lag1"] = panel[column].shift(1)
    return panel.reset_index()
