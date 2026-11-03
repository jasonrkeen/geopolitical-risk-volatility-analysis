# Amendment A1 — receipt custody and final ledger lock

**Filed November 3, 2026, before the November 30 first cutoff.** A1 supplements the [original v1 freeze](https://github.com/jasonrkeen/geopolitical-risk-volatility-analysis/tree/893944e784ce1d1f5104eb1c1529c9d132f9f8ae/research/prospective) for all 12 targets. Record both the original SHA and the full SHA of the first published commit adding this amendment on every receipt. A1 governs receipt selection, outcome recovery and ledger locking. The original model bundle, pinned sessions, target panel, eligibility criteria, primary MAE contrast and nine-month threshold continue to apply.

## The one governing receipt

1. Use the **commit-status history on the original freeze SHA** in this repository as the sole register. For target YYYY-MM, the exact context is `prospective-vix/v1/receipt/YYYY-MM`. Only statuses created by the repository owner account `jasonrkeen` count. Read every page of the individual statuses endpoint; the combined status displays the latest entry and is unsuitable for custody. [GitHub commit status API](https://docs.github.com/en/rest/commits/statuses)
2. The first matching entry, ordered by GitHub's server-generated `created_at` ascending and then numeric status ID ascending, governs irrevocably. Select it **before** checking its time or content. Record the status ID, timestamp and original target URL. The target URL must have the form `https://github.com/jasonrkeen/geopolitical-risk-volatility-analysis/commit/<full-40-hex-SHA>`. At that exact commit read `research/prospective/receipts/YYYY-MM.json`. Issue comments, branches, PR descriptions, Git author timestamps and later statuses cannot establish or replace a receipt.
3. The governing receipt must be lodged after the session close and through 23:59:59 inclusive, America/New_York, on the original cutoff date. Every source retrieval must precede or equal issuance, which must precede or equal the server timestamp. Verify the target, both protocol SHAs, all original provenance fields, finite unrounded predictions for all three models or an explicit shared exclusion, and source hashes against retained bytes. Keep the immutable receipt commit reachable. If the first entry is too early, late, malformed, unverifiable or explicitly excludes, exclude that month for all three models and record why. If no entry exists by cutoff, record a missed receipt. A later valid entry cannot cure any of these cases. If a valid first entry exists, all duplicates and subsequent edits are ignored.

## Outcome retrieval and retry deadline

For each timely, valid forecast, V is the original fixed vintage date (calendar month-end plus 10 days). Request **only V** from ALFRED. Use one attempt in each of three windows: **12:00:00 through 12:59:59 America/New_York on V+1, V+4 and V+7 calendar days**, weekends and holidays included. Start with V+1 and stop on the first response that passes all original outcome checks. Keep the first returned response for each attempt. Log request/completion times, vintage, response hash and verification result, or the transport error or missed window. A response must be received within its window.

The per-target recovery deadline is **12:59:59 Eastern on V+7**. No manual retry, alternate vintage, replacement source, or late retrieval counts. Once an attempt is missed, log the protocol deviation; use the remaining prescribed windows. If none yields a verified outcome, mark the row OUTCOME_UNSCORABLE and retain the failed-attempt evidence. For November 2027, V is December 10. The attempt dates are December 11, 14 and 17, and the final deadline is **December 17, 2027 at 12:59:59 Eastern**.

## Lock all statuses before scoring

After the final recovery deadline and **before computing any losses**, prepare one ledger with exactly one row per month, December 2026 through November 2027, in calendar order. Assign exactly one terminal status per row:

- **FORECAST_EXCLUDED** — missing, invalid or excluding governing receipt. Keep its reason and status ID if present. No outcome is required.
- **OUTCOME_UNSCORABLE** — valid issued forecasts but no verified outcome by the deadline. Keep the receipt pointer, attempt log and reason.
- **SCORED** — eligible for all three models. Keep the receipt pointer, first successful attempt, immutable evidence hashes and verified monthly actual. No loss values belong in the lock.

Publish the ledger at `research/prospective/locks/v1.csv` in a commit and register its full commit URL on the original freeze SHA using the owner-only context `prospective-vix/v1/ledger-lock`. The first entry governs by the same server-time and ID rule as receipts. Verify that it follows the final deadline, all 12 unique targets are present, each status agrees with its evidence, and there are no pending rows. A missing or invalid lock means no official v1 score; a later lock cannot substitute. Record its status ID and commit SHA in the results. Only then compute the frozen metrics once on the SCORED rows. Publish all exclusion counts and reasons. Later evidence belongs in a separately labeled audit and cannot change v1 membership.

## Boundary cases

| Case | Required disposition |
|---|---|
| First owner entry is malformed; second entry is valid before cutoff | FORECAST_EXCLUDED |
| Two entries share the cutoff second; lower ID contains a valid forecast | Lower ID governs |
| A valid receipt has no verified outcome until V+7 at 12:59:59 Eastern | SCORED if that response passes verification |
| First verified response arrives at 13:00:00 Eastern on V+7 | OUTCOME_UNSCORABLE |
| Ledger has eleven terminal rows or a duplicate target | No official v1 score |
