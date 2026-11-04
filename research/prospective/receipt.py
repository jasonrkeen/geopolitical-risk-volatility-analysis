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
                record["lookup_sha256"] = sha256(history).hexdigest()
                commit = json.loads(history)[0]
                commit_time = pd.Timestamp(commit["commit"]["committer"]["date"])
                if commit_time > min(pd.Timestamp(now()), pd.Timestamp(DAY + "T23:59:59Z")):
                    raise ValueError("GPR commit exceeds eligible time")
                url = gpr_url(commit["sha"])
                record.update(url=url, gpr_sha=commit["sha"],
                              gpr_committer_time_utc=commit_time.isoformat())
            raw = download(url)
            record["retrieved_at"] = now().isoformat()
            (vault / name).write_bytes(raw)
            record["sha256"] = sha256(raw).hexdigest()
        except (requests.RequestException, ValueError, IndexError, KeyError, TypeError) as exc:
            record.update(error=str(exc), attempted_at=now().isoformat())
        sources[name] = record
    (vault / "manifest.json").write_text(json.dumps(sources, indent=2), encoding="utf8")


def retained_bytes(vault: Path, sources: dict) -> dict[str, bytes]:
    """Check custody independently of forecast eligibility, even for exclusions."""
    if set(sources) != {*SERIES, "GPR"}:
        raise ValueError("Incomplete source manifest")
    evidence = {}
    for name, record in sources.items():
        claims = [(name, "sha256")]
        if name == "GPR":
            claims.append(("gpr_lookup.json", "lookup_sha256"))
        for filename, field in claims:
            path = vault / filename
            digest = record.get(field)
            if digest is None and "error" in record and not path.exists():
                continue
            data = path.read_bytes()
            if sha256(data).hexdigest() != digest:
                raise ValueError(f"{filename} retained evidence hash mismatch")
            evidence[filename] = data
    return evidence


def build(vault: Path, issued: datetime) -> dict:
    window(issued)
    sources = json.loads((vault / "manifest.json").read_text(encoding="utf8"))
    receipt = dict(target=TARGET, cutoff=CLOSE.isoformat(), issued_at=issued.isoformat(),
                   protocol_sha=FREEZE, amendment_sha=AMENDMENT, sources=sources,
                   feature_periods=dict(vix="2026-11", brent="2026-10", fed="2026-10", gpr="2026-10"))
    evidence = retained_bytes(vault, sources)
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
            raw = evidence[name]
            if name == "GPR":
                lookup = evidence["gpr_lookup.json"]
                meta = json.loads(lookup)[0]
                commit_time = pd.Timestamp(meta["commit"]["committer"]["date"])
                if (r["url"] != gpr_url(meta["sha"]) or r["gpr_sha"] != meta["sha"]
                        or commit_time != pd.Timestamp(r["gpr_committer_time_utc"])
                        or commit_time > min(pd.Timestamp(stamp), pd.Timestamp(DAY + "T23:59:59Z"))):
                    raise ValueError("Invalid GPR provenance")
                gpr = pd.read_excel(BytesIO(raw), usecols=["month", *COUNTRIES]).set_index("month")
                months = pd.to_datetime(gpr.index, errors="coerce")
                if months.hasnans:
                    raise ValueError("Malformed observation date in GPR")
                gpr.index = months.to_period("M")
                if not gpr.index.is_unique:
                    raise ValueError("Duplicate GPR months")
            else:
                df = pd.read_csv(BytesIO(raw), index_col=0)
                dates = pd.to_datetime(df.index, format="%Y-%m-%d", errors="coerce")
                if dates.hasnans:
                    raise ValueError(f"Malformed observation date in {name}")
                df.index = dates
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


def receipt_content(receipt: dict) -> bytes:
    return json.dumps(receipt, indent=2, allow_nan=False).encode() + b"\n"


def recover(vault: Path) -> dict:
    """Reconcile the first registered entry using GETs only, at any time."""
    first = governing()
    audit = {"first": first, "checked_at": now().isoformat(), "disposition": "NO_ENTRY"}
    if first is not None:
        try:
            url = first.get("target_url") or ""
            match = re.fullmatch(re.escape(f"https://github.com/{REPO}/commit/") + r"([0-9a-f]{40})", url)
            if not match:
                raise ValueError("Invalid immutable target URL")
            server = datetime.fromisoformat(first["created_at"].replace("Z", "+00:00"))
            window(server)
            stored = api(f"repos/{REPO}/contents/{RECEIPT}?ref={match[1]}")
            remote = base64.b64decode("".join(stored["content"].split()), validate=True)
            receipt = json.loads((vault / "receipt.json").read_text(encoding="utf8"))
            if remote != receipt_content(receipt):
                raise ValueError("Governing receipt differs from the prepared candidate")
            issued = datetime.fromisoformat(receipt["issued_at"])
            if issued > server or receipt != build(vault, issued):
                raise ValueError("Governing receipt failed issuance or provenance validation")
            audit["disposition"] = "FORECAST_EXCLUDED" if "exclusion" in receipt else "VERIFIED_FORECAST"
            if "exclusion" in receipt:
                audit["reason"] = receipt["exclusion"]
        except (ValueError, KeyError, TypeError, OSError) as exc:
            audit.update(disposition="FORECAST_EXCLUDED", reason=str(exc))
        except subprocess.CalledProcessError:
            audit.update(disposition="UNVERIFIED", reason="GitHub read failed; retry recovery")
    elif now() > CLOSE:
        audit["disposition"] = "MISSED_RECEIPT"
    # Keep the original publish response if present. Replace atomically after reconciliation.
    path = vault / "registration.json"
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf8"))
        if "response" in prior:
            audit["response"] = prior["response"]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(audit, indent=2), encoding="utf8")
    tmp.replace(path)
    return audit


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
    content = receipt_content(receipt)
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
    parser.add_argument("action", choices=["prepare", "register", "recover"])
    parser.add_argument("--vault", type=Path, required=True, help="External private evidence directory")
    args = parser.parse_args()
    vault = args.vault.resolve()
    if vault.is_relative_to(ROOT):
        parser.error("Keep retained evidence outside the repository")
    if args.action == "recover":
        audit = recover(vault)
        print("Read-only reconciliation:", audit["disposition"], audit.get("reason", ""))
        return
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
