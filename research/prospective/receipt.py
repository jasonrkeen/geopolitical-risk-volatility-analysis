"""Owner-run receipt workflow for the 2026-12 VIX target (Amendment A1)."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo
from zipfile import BadZipFile

from xlrd.biffh import XLRDError

import pandas as pd
import requests

from research.forecast_origin import COUNTRIES, GPR_PATH, GPR_REPO, ROOT, SERIES, Snapshot, features

FREEZE = "893944e784ce1d1f5104eb1c1529c9d132f9f8ae"
AMENDMENT = "2d58c32afb1197a4f5103b6e9bc0a1200aa78bfc"
OWNER = "jasonrkeen"
REPO = f"{OWNER}/geopolitical-risk-volatility-analysis"
TARGET = "2026-12"
DAY = "2026-11-30"
CONTEXT = f"prospective-vix/v1/receipt/{TARGET}"
BRANCH = f"receipts/{TARGET}"
RECEIPT = f"research/prospective/receipts/{TARGET}.json"
EASTERN = ZoneInfo("America/New_York")
OPEN = datetime(2026, 11, 30, 16, 30, tzinfo=EASTERN)
CLOSE = datetime(2026, 11, 30, 23, 59, 59, tzinfo=EASTERN)


def now() -> datetime:
    return datetime.now(timezone.utc)


def window(stamp: datetime) -> None:
    if stamp.tzinfo is None or not OPEN <= stamp <= CLOSE:
        raise ValueError("Outside the November 30 issuance window (16:30–23:59:59 Eastern)")


def frozen(name: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{FREEZE}:research/prospective/{name}"], cwd=ROOT, stdin=subprocess.DEVNULL, stderr=subprocess.PIPE)


def download(url: str) -> bytes:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content


def gpr_url(sha: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid GPR commit SHA")
    return f"https://raw.githubusercontent.com/{GPR_REPO}/{sha}/{GPR_PATH}"


def capture(vault: Path) -> None:
    window(now())
    vault.mkdir(parents=True, exist_ok=False)
    sources = {}
    for name in (*SERIES, "GPR"):
        url = (f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={name}&vintage_date={DAY}"
               if name != "GPR" else f"https://api.github.com/repos/{GPR_REPO}/commits"
               f"?path={GPR_PATH}&until={DAY}T23:59:59Z&per_page=1")
        record = {"url": url, "vintage": DAY}
        try:
            if name == "GPR":
                history = download(url)
                (vault / "gpr_lookup.json").write_bytes(history)
                commit = json.loads(history)[0]
                commit_time = pd.Timestamp(commit["commit"]["committer"]["date"])
                if commit_time > min(pd.Timestamp(now()), pd.Timestamp(DAY + "T23:59:59Z")):
                    raise ValueError("GPR commit exceeds eligible time")
                url = gpr_url(commit["sha"])
                record.update(url=url, gpr_sha=commit["sha"], lookup_sha256=sha256(history).hexdigest(),
                              gpr_committer_time_utc=commit_time.isoformat())
            raw = download(url)
            record["retrieved_at"] = now().isoformat()
            (vault / name).write_bytes(raw)
            record["sha256"] = sha256(raw).hexdigest()
        except (requests.RequestException, ValueError, IndexError, KeyError, TypeError) as exc:
            record.update(error=str(exc), attempted_at=now().isoformat())
        sources[name] = record
    (vault / "manifest.json").write_text(json.dumps(sources, indent=2), encoding="utf8")


def build(vault: Path, issued: datetime) -> dict:
    window(issued)
    sources = json.loads((vault / "manifest.json").read_text(encoding="utf8"))
    receipt = dict(target=TARGET, cutoff=CLOSE.isoformat(), issued_at=issued.isoformat(),
                   protocol_sha=FREEZE, amendment_sha=AMENDMENT, sources=sources,
                   feature_periods=dict(vix="2026-11", brent="2026-10", fed="2026-10", gpr="2026-10"))
    fred = {}
    try:
        for name in (*SERIES, "GPR"):
            r = sources[name]
            stamp = datetime.fromisoformat(r.get("retrieved_at") or r["attempted_at"])
            window(stamp)
            if stamp > issued or r["vintage"] != DAY:
                raise ValueError(f"Invalid provenance for {name}")
            if "error" in r:
                raise ValueError(f"{name} acquisition failed: {r['error']}")
            raw = (vault / name).read_bytes()
            if sha256(raw).hexdigest() != r["sha256"]:
                raise ValueError(f"{name} source hash mismatch")
            if name == "GPR":
                lookup = (vault / "gpr_lookup.json").read_bytes()
                meta = json.loads(lookup)[0]
                commit_time = pd.Timestamp(meta["commit"]["committer"]["date"])
                if (r["url"] != gpr_url(meta["sha"]) or r["gpr_sha"] != meta["sha"]
                        or sha256(lookup).hexdigest() != r["lookup_sha256"]
                        or commit_time != pd.Timestamp(r["gpr_committer_time_utc"])
                        or commit_time > min(pd.Timestamp(stamp), pd.Timestamp(DAY + "T23:59:59Z"))):
                    raise ValueError("Invalid GPR provenance")
                gpr = pd.read_excel(BytesIO(raw), usecols=["month", *COUNTRIES]).set_index("month")
                gpr.index = pd.to_datetime(gpr.index).to_period("M")
                if not gpr.index.is_unique:
                    raise ValueError("Duplicate GPR months")
            else:
                df = pd.read_csv(BytesIO(raw), index_col=0, parse_dates=True)
                if (r["url"] != f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={name}&vintage_date={DAY}"
                        or list(df.columns) != [f"{name}_20261130"] or not df.index.is_unique):
                    raise ValueError(f"Invalid {name} vintage or duplicate dates")
                fred[name] = df.sort_index().loc[:DAY].iloc[:, 0].dropna()
        expected = pd.to_datetime(pd.read_csv(BytesIO(frozen("sessions.csv")))["session_date"])
        expected = pd.DatetimeIndex(expected[expected.dt.to_period("M") == "2026-11"])
        observed = fred["VIXCLS"].index
        if not expected.equals(observed[observed.to_period("M") == "2026-11"]):
            raise ValueError("VIX coverage differs from frozen November sessions")
        row = features(pd.Period(TARGET, "M"), Snapshot(fred, gpr.rename(columns=COUNTRIES), []))
        receipt["feature_periods"]["cpi"] = row["cpi_month"]
        models = json.loads(frozen("models.json"))["models"]
        values = {name: float(row[name]) for name in models["enhanced"] if name != "const"}
        if not all(map(math.isfinite, values.values())):
            raise ValueError("Missing or nonfinite model input")
        predictions = {key: coeff["const"] + sum(w * values[k] for k, w in coeff.items() if k != "const")
                       for key, coeff in models.items()}
        if not all(map(math.isfinite, predictions.values())):
            raise ValueError("Nonfinite prediction")
        receipt.update(features=values, predictions=predictions)
    except (ValueError, KeyError, IndexError, TypeError, OSError, ZeroDivisionError, BadZipFile, XLRDError) as exc:
        receipt["exclusion"] = str(exc)
    return receipt


def api(path: str, payload: dict | None = None, paginate: bool = False):
    cmd = ["gh", "api", path]
    if paginate:
        cmd += ["--paginate", "--slurp"]
    if payload is not None:
        cmd += ["--method", "POST", "--input", "-"]
    return json.loads(subprocess.check_output(cmd, input=None if payload is None else json.dumps(payload).encode()))


def governing() -> dict | None:
    pages = api(f"repos/{REPO}/commits/{FREEZE}/statuses?per_page=100", paginate=True)
    candidates = (s for page in pages for s in page if s["creator"]["login"] == OWNER
                  and s["context"] == CONTEXT)
    return min(candidates, key=lambda s: (s["created_at"], s["id"]), default=None)


def publish(vault: Path, receipt: dict) -> int:
    window(now())
    if api("user")["login"] != OWNER:
        raise ValueError("Registration requires the repository owner account")
    existing = governing()
    if existing:
        raise ValueError(f"Owner status {existing['id']} already governs; inspect it before any retry")
    if receipt != build(vault, datetime.fromisoformat(receipt["issued_at"])):
        raise ValueError("Receipt does not match retained evidence")
    # The dedicated branch is create-only. Never replace or delete a receipt.
    content = json.dumps(receipt, indent=2, allow_nan=False).encode() + b"\n"
    encoded = base64.b64encode(content).decode()
    root = f"repos/{REPO}"
    anchor_tree = api(f"{root}/git/commits/{AMENDMENT}")["tree"]["sha"]
    tree = api(f"{root}/git/trees", {"base_tree": anchor_tree, "tree": [
        {"path": RECEIPT, "mode": "100644", "type": "blob", "content": content.decode()}]})
    commit = api(f"{root}/git/commits", {"message": f"File {TARGET} prospective VIX receipt",
                 "parents": [AMENDMENT], "tree": tree["sha"]})
    prefix = "refs/heads/"
    refs = api(f"{root}/git/matching-refs/heads/{BRANCH}")
    exact = next((r for r in refs if r["ref"] == prefix + BRANCH), None)
    if exact is None:
        api(f"{root}/git/refs", {"ref": prefix + BRANCH, "sha": commit["sha"]})
        sha = commit["sha"]
    else:
        sha = exact["object"]["sha"]
    stored = api(f"{root}/contents/{RECEIPT}?ref={sha}")
    if "".join(stored["content"].split()) != encoded:
        raise ValueError("Reachable branch contains a different receipt; refusing replacement")
    if governing():
        raise ValueError("An owner status already governs")
    checked_at = now()
    window(checked_at)
    if checked_at.replace(microsecond=0) < datetime.fromisoformat(receipt["issued_at"]):
        raise ValueError("Wait until the next second before registering the issued receipt")
    result = api(f"{root}/statuses/{FREEZE}", {"context": CONTEXT, "state": "success",
                 "target_url": f"https://github.com/{REPO}/commit/{sha}",
                 "description": "Filed shared exclusion" if "exclusion" in receipt else "Filed three predictions"})
    first = governing()
    (vault / "registration.json").write_text(json.dumps({"response": result, "first": first},
                                                       indent=2), encoding="utf8")
    target_url = f"https://github.com/{REPO}/commit/{sha}"
    if not first or first["id"] != result["id"] or first["target_url"] != target_url:
        raise ValueError("Registration did not become the governing entry")
    server = datetime.fromisoformat(first["created_at"].replace("Z", "+00:00"))
    window(server)
    if server < datetime.fromisoformat(receipt["issued_at"]):
        raise ValueError("Server timestamp precedes issuance")
    return first["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "register"])
    parser.add_argument("--vault", type=Path, required=True, help="External private evidence directory")
    args = parser.parse_args()
    vault = args.vault.resolve()
    if vault.is_relative_to(ROOT):
        parser.error("Keep retained evidence outside the repository")
    window(now())
    path = vault / "receipt.json"
    if args.action == "prepare":
        capture(vault)
        receipt = build(vault, now())
        issued = now()
        window(issued)
        receipt["issued_at"] = issued.isoformat()
        path.write_text(json.dumps(receipt, indent=2, allow_nan=False), encoding="utf8")
        print("Prepared local receipt:", path)
    else:
        receipt = json.loads(path.read_text(encoding="utf8"))
        print("Governing GitHub status ID:", publish(vault, receipt))


if __name__ == "__main__":
    main()
