# November 30 receipt workflow

This manual workflow prepares the December 2026 target under [Amendment A1](amendment-a1.md). Run it from a full clone with the frozen commits available, the research requirements installed, and GitHub CLI authenticated as **jasonrkeen** for registration. The owner account needs repository contents and commit-status write access. Both commands use the real clock. The operational window opens conservatively at **16:30 Eastern on November 30, 2026** and closes at **23:59:59 Eastern**.

## Rehearse offline

Run `python -m pytest -q tests/test_forecast_receipt.py`. The tests construct synthetic daily and monthly CSV files and a legacy GPR workbook. GitHub and the source downloads are replaced in the tests. There is no timer, scheduled dispatch, or clock override on the operator command.

## Cutoff-day procedure

1. Choose a new, private evidence directory outside the checkout that can be retained through scoring and audit. Run `python -m research.prospective.receipt prepare --vault ../private-vix-2026-11-30`. The command retrieves the four issue-date ALFRED inputs and the eligible GPR revision, retains their bytes, and records retrieval timestamps, hashes, source periods and commit metadata. It reads coefficients and sessions from the original frozen Git objects. Inspect the local `receipt.json` for either three finite predictions or a shared exclusion. Finish this step well before the deadline.
2. To lodge that exact candidate, run `python -m research.prospective.receipt register --vault ../private-vix-2026-11-30`. This is the live publication command. It rebuilds the receipt from retained evidence, writes only the receipt JSON into an immutable Git commit, and keeps it reachable on the create-only `receipts/2026-12` branch. It then registers the A1 context on the original freeze SHA, retrieves all status pages, and checks the governing ID, URL and server timestamp. Keep the printed ID and private `registration.json`.
3. After an interrupted registration, inspect the individual statuses on the original freeze SHA first. If an owner entry exists, record the earliest by server time then numeric ID, even if invalid. Never replace it. If none exists, repeat registration with the same vault while the window is open. A reachable receipt must match byte-for-byte. Preserve that branch and retain the vault separately; the receipt exposes the evidence hashes, not the raw source files. If the deadline passes with no owner entry, log a missed receipt.
