"""Reconstruct and score month-end forecasts from historical source versions."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/forecast_origin"
FIRST_TARGET = pd.Period("2023-01", "M")
LAST_TARGET = pd.Period("2025-12", "M")
SERIES = ("VIXCLS", "DCOILBRENTEU", "FEDFUNDS", "CPIAUCSL")
COUNTRIES = {"GPRC_USA": "gpr_usa", "GPRC_CHN": "gpr_china", "GPRC_RUS": "gpr_russia"}
CONTROLS = ["vix", "brent", "fed", "inflation", "covid", "war"]
MODELS = {"baseline": ["vix"], "controls": CONTROLS, "enhanced": CONTROLS + list(COUNTRIES.values())}
GPR_REPO = "iacoviel/iacoviel.github.io"
GPR_PATH = "gpr_files/data_gpr_export.xls"


@dataclass
class Snapshot:
    fred: dict[str, pd.Series]
    gpr: pd.DataFrame
    manifest: list[dict]


def fetch(url: str, path: Path) -> bytes:
    if path.exists():
        return path.read_bytes()
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=45)
            response.raise_for_status()
            path.write_bytes(response.content)
            return response.content
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(url)


def snapshot(cutoff: pd.Timestamp, cache: Path, pins: dict) -> Snapshot:
    day = cutoff.strftime("%Y-%m-%d")
    folder = cache / day
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    fred = {}
    for name in SERIES:
        url = f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={name}&vintage_date={day}"
        raw = fetch(url, folder / (name + ".csv"))
        df = pd.read_csv(BytesIO(raw), index_col=0, parse_dates=True)
        if list(df.columns) != [f"{name}_{cutoff:%Y%m%d}"]:
            raise ValueError(f"Unexpected vintage for {name} at {day}")
        fred[name] = df.loc[df.index <= cutoff].iloc[:, 0].dropna().sort_index()
        manifest.append(dict(cutoff=day, series=name, url=url, sha256=hashlib.sha256(raw).hexdigest()))
    meta = folder / "gpr_commit.json"
    if (day, "GPR") in pins:
        record = pins[day, "GPR"]
        sha = record["url"].split("/")[5]
        gpr_committer_time_utc = record["gpr_committer_time_utc"]
    elif meta.exists():
        sha, gpr_committer_time_utc = json.loads(meta.read_text())
    else:
        # Use a conservative UTC day boundary before the US evening cutoff.
        endpoint = f"repos/{GPR_REPO}/commits?path={GPR_PATH}&until={day}T23:59:59Z&per_page=1"
        commit = json.loads(subprocess.check_output(["gh", "api", endpoint]))[0]
        sha, gpr_committer_time_utc = commit["sha"], commit["commit"]["committer"]["date"]
        meta.write_text(json.dumps([sha, gpr_committer_time_utc]))
    if gpr_committer_time_utc[:10] > day:
        raise ValueError(f"GPR commit after cutoff {day}")
    url = f"https://raw.githubusercontent.com/{GPR_REPO}/{sha}/{GPR_PATH}"
    raw = fetch(url, folder / "gpr.xls")
    gpr = pd.read_excel(BytesIO(raw), usecols=["month", *COUNTRIES]).set_index("month")
    gpr.index = pd.to_datetime(gpr.index).to_period("M")
    manifest.append(dict(cutoff=day, series="GPR", url=url, gpr_committer_time_utc=gpr_committer_time_utc,
                         sha256=hashlib.sha256(raw).hexdigest()))
    for row in manifest:
        if pins and row["sha256"] != pins[day, row["series"]]["sha256"]:
            raise ValueError(f"Source hash mismatch for {day} {row['series']}")
    return Snapshot(fred, gpr.rename(columns=COUNTRIES), manifest)


def features(target: pd.Period, data: Snapshot) -> dict:
    origin = target - 1
    ref = target - 2
    def daily(name: str, month: pd.Period) -> pd.Series:
        s = data.fred[name]
        return s[s.index.to_period("M") == month]

    vix = daily("VIXCLS", origin)
    oil = daily("DCOILBRENTEU", ref)
    cpi = data.fred["CPIAUCSL"].copy()
    cpi.index = cpi.index.to_period("M")
    eligible = cpi[cpi.index <= ref]
    latest = eligible.index.max()
    inflation = (eligible.iloc[-1] / cpi.get(latest - 12, np.nan) - 1) * 100
    gpr = data.gpr.reindex([ref]).iloc[0]
    fed = data.fred["FEDFUNDS"].get(ref.start_time, np.nan)
    return dict(vix=vix.mean(), brent=oil.mean(), fed=fed, inflation=inflation,
                **gpr.to_dict(), covid=int("2020-03" <= str(target) <= "2020-12"),
                war=int("2022-02" <= str(target) <= "2022-12"),
                vix_last=vix.index.max(), brent_last=oil.index.max(),
                fed_month=str(ref), cpi_month=str(latest), gpr_month=str(ref))


def run(cache: Path) -> None:
    panel = pd.read_csv(ROOT / "data_clean/merged_monthly_data.csv", index_col="date", parse_dates=True)
    panel.index = panel.index.to_period("M")
    sessions = pd.DatetimeIndex(pd.read_csv(
        ROOT / "research/vix_sessions.csv", parse_dates=["session_date"]
    )["session_date"])
    if not sessions.is_unique or not sessions.is_monotonic_increasing:
        raise ValueError("Pinned VIX sessions must be unique and sorted")
    closes = sessions.to_series().groupby(sessions.to_period("M")).max()
    targets = pd.period_range(FIRST_TARGET, LAST_TARGET, freq="M")
    cutoffs = [closes[t - 1] for t in targets]
    manifest_path = OUTPUT / "sources.csv"
    pins = (pd.read_csv(manifest_path).set_index(["cutoff", "series"]).to_dict("index")
            if manifest_path.exists() else {})
    with ThreadPoolExecutor(max_workers=4) as pool:
        snapshots = list(pool.map(lambda c: snapshot(c, cache, pins), cutoffs))
    base = snapshots[0]
    # Use the frozen VIX calendar only to detect incomplete monthly coverage.
    # Predictor values themselves always come from the selected source vintage.
    missing_dates = []
    for target, archive in zip(targets, snapshots):
        origin = target - 1
        expected = sessions[sessions.to_period("M") == origin]
        available = archive.fred["VIXCLS"].index
        vintage_dates = available[available.to_period("M") == origin]
        differences = expected.symmetric_difference(vintage_dates)
        missing_dates.append(", ".join(differences.strftime("%Y-%m-%d")))
    if missing_dates[0]:
        raise ValueError("The final training outcome is incomplete at the fitting date")
    train_dates = pd.period_range("2011-02", FIRST_TARGET - 1, freq="M")
    train = pd.DataFrame([features(t, base) for t in train_dates], index=train_dates)
    train["actual"] = base.fred["VIXCLS"].groupby(base.fred["VIXCLS"].index.to_period("M")).mean()
    train = train.dropna(subset=["actual", *MODELS["enhanced"]])
    out = pd.DataFrame([features(t, s) for t, s in zip(targets, snapshots)], index=targets)
    out["vix_calendar_difference"] = missing_dates
    out.loc[out.vix_calendar_difference.ne(""), "vix"] = np.nan
    out["cutoff"] = cutoffs
    out["actual"] = panel.vix.reindex(targets)
    out["exclusion"] = out[MODELS["enhanced"]].apply(
        lambda row: ", ".join(row.index[row.isna()]), axis=1)
    valid = out.exclusion.eq("")
    scores = []
    for model, cols in MODELS.items():
        fit = sm.OLS(train.actual, sm.add_constant(train[cols], has_constant="add")).fit()
        pred = fit.predict(sm.add_constant(out.loc[valid, cols], has_constant="add"))
        error = out.actual - pred
        out[model + "_prediction"] = pred
        out[model + "_error"] = error
        scores.append(dict(model=model, train_n=len(train), holdout_n=int(error.notna().sum()),
                           mae=error.abs().mean(), rmse=np.sqrt(error.pow(2).mean()),
                           mape=100 * (error / out.actual).abs().mean()))
    out["gpr_minus_controls_abs_error"] = out.enhanced_error.abs() - out.controls_error.abs()
    out["gpr_minus_controls_squared_error"] = out.enhanced_error.pow(2) - out.controls_error.pow(2)
    OUTPUT.mkdir(exist_ok=True, parents=True)
    out.to_csv(OUTPUT / "monthly.csv", index_label="target")
    pd.DataFrame(scores).to_csv(OUTPUT / "scores.csv", index=False)
    pd.DataFrame([r for s in snapshots for r in s.manifest]).to_csv(OUTPUT / "sources.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True, help="Local vintage download directory")
    run(parser.parse_args().cache)
