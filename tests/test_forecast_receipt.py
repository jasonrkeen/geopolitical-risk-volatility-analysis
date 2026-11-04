from base64 import b64encode
from datetime import timedelta
from io import BytesIO
import json
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest
import requests
import xlwt

from research.prospective import receipt as workflow


@pytest.fixture
def synthetic(monkeypatch, tmp_path):
    stamp = workflow.OPEN + timedelta(minutes=15)
    monkeypatch.setattr(workflow, "now", lambda: stamp)
    sessions = pd.read_csv(BytesIO(workflow.frozen("sessions.csv"))).session_date
    dates = sessions[sessions.str.startswith("2026-11")]
    payloads = {
        "VIXCLS": list(zip(dates, [18.] * len(dates))),
        "DCOILBRENTEU": [("2026-10-01", 60), ("2026-10-02", 66)],
        "FEDFUNDS": [("2026-10-01", 4)],
        "CPIAUCSL": [("2025-10-01", 100), ("2026-10-01", 103)],
    }
    sha = "a" * 40
    def fetch(url):
        if "api.github.com" in url:
            assert "until=2026-11-30T23:59:59Z" in url
            return json.dumps([{"sha": sha, "commit": {"committer": {
                "date": "2026-11-01T14:00:00Z"}}}]).encode()
        if url == workflow.gpr_url(sha):
            workbook = BytesIO()
            book = xlwt.Workbook()
            sheet = book.add_sheet("GPR")
            for i, key in enumerate(["month", "GPRC_USA", "GPRC_CHN", "GPRC_RUS"]):
                sheet.write(0, i, key)
            for i, value in enumerate(["2026-10-01", 2, 3, 4]):
                sheet.write(1, i, value)
            book.save(workbook)
            return workbook.getvalue()
        query = parse_qs(urlparse(url).query)
        assert query["vintage_date"] == [workflow.DAY]
        name = query["id"][0]
        return pd.DataFrame(payloads[name], columns=["observation_date", name + "_20261130"]).to_csv(
            index=False).encode()
    monkeypatch.setattr(workflow, "download", fetch)
    # Any undeclared network read or GitHub operation fails the test.
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("network access"))
    monkeypatch.setattr(workflow, "api", lambda *a, **k: pytest.fail("GitHub access"))
    return tmp_path / "evidence", stamp, payloads


def test_prepare_three_models(synthetic):
    vault, stamp, _ = synthetic
    workflow.capture(vault)
    r = workflow.build(vault, stamp)
    assert r["protocol_sha"] == workflow.FREEZE and r["amendment_sha"] == workflow.AMENDMENT
    expected = dict(vix=18., brent=63., fed=4., inflation=3., covid=0., war=0.,
                    gpr_usa=2., gpr_china=3., gpr_russia=4.)
    assert r["features"] == pytest.approx(expected)
    assert r["feature_periods"]["cpi"] == "2026-10"
    for name, weights in json.loads(workflow.frozen("models.json"))["models"].items():
        assert r["predictions"][name] == pytest.approx(
            weights["const"] + sum(expected[k] * w for k, w in weights.items() if k != "const"))
    for name, record in r["sources"].items():
        assert record["sha256"] == workflow.sha256((vault / name).read_bytes()).hexdigest()


@pytest.mark.parametrize("problem", ["missing session", "missing rate", "unavailable"])
def test_exclusion_shared(synthetic, problem, monkeypatch):
    vault, stamp, inputs = synthetic
    if problem == "missing session":
        inputs["VIXCLS"].pop()
    elif problem == "missing rate":
        inputs["FEDFUNDS"].clear()
    elif problem == "unavailable":
        def unavailable(url):
            raise requests.ConnectionError("synthetic outage")
        monkeypatch.setattr(workflow, "download", unavailable)
    workflow.capture(vault)
    r = workflow.build(vault, stamp)
    assert r["exclusion"] and "predictions" not in r


def test_outside_window_and_future_retrieval(synthetic, monkeypatch):
    vault, stamp, _ = synthetic
    monkeypatch.setattr(workflow, "now", lambda: workflow.OPEN - timedelta(seconds=1))
    with pytest.raises(ValueError, match="Outside"):
        workflow.capture(vault)
    assert not vault.exists()
    monkeypatch.setattr(workflow, "now", lambda: stamp)
    workflow.capture(vault)
    assert "provenance" in workflow.build(vault, stamp - timedelta(seconds=1))["exclusion"]
    with pytest.raises(ValueError, match="Outside"):
        workflow.build(vault, workflow.CLOSE + timedelta(seconds=1))


def test_first_owner_status_across_pages(monkeypatch):
    records = [[dict(context=workflow.CONTEXT, creator={"login": "other"}, id=1, created_at="00")],
               [dict(context=workflow.CONTEXT, creator={"login": workflow.OWNER}, id=i, created_at="01")
                for i in [3, 2]]]
    def api(path, paginate=False):
        assert paginate and workflow.FREEZE in path
        return records
    monkeypatch.setattr(workflow, "api", api)
    assert workflow.governing()["id"] == 2


@pytest.mark.parametrize("exclude", [False, True])
@pytest.mark.parametrize("lose_response", [False, True])
def test_mock_registration_and_repeat(synthetic, monkeypatch, exclude, lose_response):
    vault, stamp, inputs = synthetic
    if exclude:
        inputs["VIXCLS"].pop()
    workflow.capture(vault)
    r = workflow.build(vault, stamp)
    (vault / "receipt.json").write_text(json.dumps(r))
    sha = "b" * 40
    statuses = []
    contents = {}

    def api(path, payload=None, paginate=False):
        if path == "user":
            return {"login": workflow.OWNER}
        if paginate:
            return [statuses]
        if path.endswith("/git/commits/" + workflow.AMENDMENT):
            return {"tree": {"sha": "anchor-tree"}}
        if path.endswith("/git/trees"):
            entry, = payload["tree"]
            assert entry["path"] == workflow.RECEIPT
            contents["value"] = entry["content"]
            return {"sha": "tree"}
        if path.endswith("/git/commits"):
            assert payload["parents"] == [workflow.AMENDMENT]
            return {"sha": sha}
        if "/git/matching-refs/" in path:
            return []
        if path.endswith("/git/refs"):
            assert payload["sha"] == sha
            return {}
        if "/contents/" in path:
            assert path.endswith(workflow.RECEIPT + "?ref=" + sha)
            return {"content": b64encode(contents["value"].encode()).decode()}
        assert path.endswith("/statuses/" + workflow.FREEZE)
        assert payload["context"] == workflow.CONTEXT and payload["target_url"].endswith(sha)
        status = dict(payload, id=7, created_at=stamp.isoformat(), creator={"login": workflow.OWNER})
        statuses.append(status)
        if lose_response:
            raise ConnectionError("Simulated lost response after acceptance")
        return status

    monkeypatch.setattr(workflow, "api", api)
    if lose_response:
        with pytest.raises(ConnectionError):
            workflow.publish(vault, r)
        assert not (vault / "registration.json").exists()
        monkeypatch.setattr(workflow, "now", lambda: workflow.CLOSE + timedelta(days=1))
        def read_only(path, payload=None, paginate=False):
            assert payload is None and (paginate or "/contents/" in path)
            return api(path, paginate=paginate)
        monkeypatch.setattr(workflow, "api", read_only)
        audit = workflow.recover(vault)
        assert audit == json.loads((vault / "registration.json").read_text())
        assert audit["first"] == statuses[0]
        assert audit["disposition"] == ("FORECAST_EXCLUDED" if exclude else "VERIFIED_FORECAST")
        assert len(statuses) == 1
        return
    assert workflow.publish(vault, r) == 7
    assert json.loads(contents["value"]) == r
    assert ("exclusion" in r) == exclude
    with pytest.raises(ValueError, match="already governs"):
        workflow.publish(vault, r)
    assert len(statuses) == 1

def test_non_owner_cannot_write(synthetic, monkeypatch):
    vault, stamp, _ = synthetic
    workflow.capture(vault)
    r = workflow.build(vault, stamp)
    def api(path, *args, **kwargs):
        assert path == "user"
        return {"login": "github-actions[bot]"}
    monkeypatch.setattr(workflow, "api", api)
    with pytest.raises(ValueError, match="owner"):
        workflow.publish(vault, r)

@pytest.mark.parametrize("filename", ["GPR", "CPIAUCSL", "gpr_lookup.json"])
@pytest.mark.parametrize("damage", ["delete", "alter"])
def test_earlier_exclusion_cannot_hide_damaged_evidence(synthetic, monkeypatch, filename, damage):
    vault, stamp, _ = synthetic
    fetch = workflow.download
    def outage(url):
        if "id=VIXCLS" in url:
            raise requests.ConnectionError("synthetic VIX outage")
        return fetch(url)
    monkeypatch.setattr(workflow, "download", outage)
    workflow.capture(vault)
    receipt = workflow.build(vault, stamp)
    assert "VIXCLS acquisition failed" in receipt["exclusion"]
    path = vault / filename
    if damage == "delete":
        path.unlink()
    else:
        path.write_bytes(b"altered")
    def read_only(endpoint, paginate=False):
        if endpoint == "user":
            return {"login": workflow.OWNER}
        assert paginate and "/statuses" in endpoint
        return [[]]
    monkeypatch.setattr(workflow, "api", read_only)
    with pytest.raises((FileNotFoundError, ValueError)):
        workflow.publish(vault, receipt)


@pytest.mark.parametrize("series", workflow.SERIES)
def test_malformed_source_date_is_one_shared_exclusion(synthetic, series):
    vault, stamp, inputs = synthetic
    inputs[series].append(("not-a-date", 2))
    workflow.capture(vault)
    receipt = workflow.build(vault, stamp)
    assert receipt["exclusion"] == f"Malformed observation date in {series}"
    assert "predictions" not in receipt
    assert receipt["sources"][series]["sha256"] == workflow.sha256((vault / series).read_bytes()).hexdigest()


@pytest.mark.parametrize("fault", ["late", "different bytes", "wrong URL", "absent"])
def test_recovery_never_substitutes_another_receipt(synthetic, monkeypatch, fault):
    vault, stamp, _ = synthetic
    workflow.capture(vault)
    receipt = workflow.build(vault, stamp)
    (vault / "receipt.json").write_text(json.dumps(receipt))
    first = dict(context=workflow.CONTEXT, creator={"login": workflow.OWNER}, id=2,
                 created_at=(workflow.CLOSE + timedelta(seconds=1) if fault == "late" else stamp).isoformat(),
                 target_url=f"https://github.com/{workflow.REPO}/commit/" + "b"*40)
    if fault == "wrong URL":
        first["target_url"] = "https://example.org/wrong"
    def read_only(endpoint, paginate=False):
        if paginate:
            return [[]] if fault == "absent" else [[dict(first, id=3)], [first]]
        assert fault == "different bytes" and endpoint.endswith("b"*40)
        return {"content": b64encode(b"another receipt").decode()}
    monkeypatch.setattr(workflow, "api", read_only)
    monkeypatch.setattr(workflow, "now", lambda: workflow.CLOSE + timedelta(days=1))
    monkeypatch.setattr("sys.argv", ["receipt", "recover", "--vault", str(vault)])
    workflow.main()
    audit = json.loads((vault / "registration.json").read_text())
    if fault == "absent":
        assert audit["disposition"] == "MISSED_RECEIPT" and audit["first"] is None
    else:
        assert audit["disposition"] == "FORECAST_EXCLUDED" and audit["first"] == first


def test_lookup_is_verified_when_gpr_workbook_download_fails(synthetic, monkeypatch):
    vault, stamp, _ = synthetic
    fetch = workflow.download
    def unavailable(url):
        if url.startswith("https://raw.githubusercontent.com/"):
            raise requests.ConnectionError("synthetic GPR outage")
        return fetch(url)
    monkeypatch.setattr(workflow, "download", unavailable)
    workflow.capture(vault)
    receipt = workflow.build(vault, stamp)
    assert "GPR acquisition failed" in receipt["exclusion"]
    (vault / "gpr_lookup.json").write_bytes(b"changed")
    with pytest.raises(ValueError, match="lookup.*hash mismatch"):
        workflow.build(vault, stamp)


def test_malformed_gpr_date_is_a_shared_exclusion(synthetic, monkeypatch):
    vault, stamp, _ = synthetic
    fetch = workflow.download
    def malformed(url):
        if not url.startswith("https://raw.githubusercontent.com/"):
            return fetch(url)
        stream = BytesIO()
        book = xlwt.Workbook()
        sheet = book.add_sheet("GPR")
        for i, (key, value) in enumerate(zip(["month", *workflow.COUNTRIES], ["bad-date", 2, 3, 4])):
            sheet.write(0, i, key)
            sheet.write(1, i, value)
        book.save(stream)
        return stream.getvalue()
    monkeypatch.setattr(workflow, "download", malformed)
    workflow.capture(vault)
    receipt = workflow.build(vault, stamp)
    assert receipt["exclusion"] == "Malformed observation date in GPR" and "predictions" not in receipt
