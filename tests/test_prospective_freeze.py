from pathlib import Path
import json

import numpy as np
import pandas as pd

from research.forecast_origin import MODELS, OUTPUT

FREEZE = Path(__file__).resolve().parents[1] / "research/prospective"


def test_frozen_coefficients_reproduce_development_predictions() -> None:
    bundle = json.loads((FREEZE / "models.json").read_text())
    ledger = pd.read_csv(OUTPUT / "monthly.csv").dropna(subset=["baseline_prediction"])
    assert len(ledger) == 34 and bundle["training_months"] == 143
    assert set(bundle["models"]) == set(MODELS)
    for model, features in MODELS.items():
        weights = bundle["models"][model]
        assert list(weights) == ["const", *features]
        predictions = ledger[features] @ pd.Series({name: weights[name] for name in features})
        np.testing.assert_allclose(predictions + weights["const"], ledger[model + "_prediction"],
                                   atol=1e-10, rtol=0)


def test_calendar_covers_every_origin_and_target() -> None:
    sessions = pd.DatetimeIndex(pd.read_csv(FREEZE / "sessions.csv", parse_dates=["session_date"]).session_date)
    assert sessions.is_unique and sessions.is_monotonic_increasing
    assert sessions.to_period("M").unique().equals(pd.period_range("2026-11", "2027-11", freq="M"))
    assert sessions[sessions.to_period("M") == "2026-11"][-1] == pd.Timestamp("2026-11-30")
    assert pd.Timestamp("2026-11-27") in sessions and pd.Timestamp("2026-11-26") not in sessions
