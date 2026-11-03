# Prospective VIX evaluation v1

**Filed November 3, 2026.** The fixed evaluation panel is the 12 monthly targets from December 2026 through November 2027. The first issue date is November 30, 2026. January 2026 through November 2026 are outside the study. The 2023–2025 backtest is development evidence. The first published GitHub revision containing this protocol, the coefficients, and the calendar is the v1 freeze. Record that SHA on every forecast. Amendments require a separately dated version and cannot replace the v1 result.

## Models and question

Does adding country GPR reduce absolute VIX forecast error relative to the otherwise identical controls-only model? [models.json](models.json) fixes the intercept and all coefficients of the three PR #2 OLS specifications. Each prediction equals its intercept plus the sum of coefficient times feature, in original units, at full precision. Use the baseline (prior VIX), controls (prior VIX, Brent, federal funds, CPI inflation and the two crisis flags), and enhanced (controls plus US, China and Russia GPR). Both crisis flags are zero throughout this evaluation. Use one fixed fit for every origin, without updating parameters, transformations or model selection.

Training used February 2011–December 2022 and the December 30, 2022 fitting vintage (143 months). The three models reproduce the archived predictions on the previously inspected dates to within 1e-10 VIX points. The implementation and five fitting-source hashes are pinned in [the merged research code](https://github.com/jasonrkeen/geopolitical-risk-volatility-analysis/blob/22d1d78d17ac1f9dbb083ada89024e523d11e155/research/forecast_origin.py) and [source manifest](https://github.com/jasonrkeen/geopolitical-risk-volatility-analysis/blob/22d1d78d17ac1f9dbb083ada89024e523d11e155/outputs/forecast_origin/sources.csv).

## Issue cutoff and custody

For target month T, issue after the close and **by 23:59:59 America/New_York on the last pinned regular session of T−1**. The [session list](sessions.csv) covers origin and target dates. It uses weekdays minus full Cboe C1 regular-session holidays, including early closes as sessions. It is independent of outcome prices. Keep the filed calendar if an unexpected closure creates a missing session and record the resulting exclusion. [Cboe US options holiday schedule](https://www.cboe.com/about/hours/us-options)

Use the issue-date ALFRED vintage and only source bytes actually retrieved by issuance. Discard observations dated after the cutoff. Apply the following rules identically for the three models.

| Feature | Frozen rule for T |
|---|---|
| Prior VIX | Mean VIXCLS daily closes in T−1. Require the set of nonmissing dates to equal the pinned sessions for that month. |
| Brent | Mean of the available DCOILBRENTEU daily prices in T−2. At least one finite observation is required, as in the historical model. |
| Federal funds | FEDFUNDS for T−2. |
| Inflation | In the cutoff CPIAUCSL vintage, use the latest nonmissing reference month at or before T−2. Compute 100 × (index / index exactly 12 calendar months earlier − 1). Preserve absent observations. |
| Country GPR | Use GPRC_USA, GPRC_CHN, GPRC_RUS for T−2. Select the latest eligible publisher workbook commit under the historical rule (committer time no later than 23:59:59 UTC on issue date), available at retrieval. Record actual retrieval time separately. Git committer time is a publication proxy. |

Before the deadline, lodge a GitHub timestamped forecast receipt with target, issue time, protocol SHA, source URLs, vintage dates, retrieval timestamps, file hashes, GPR SHA, feature periods/values and all three unrounded predictions or one exclusion reason. Retain the source bytes for verification. A local Git timestamp alone is insufficient. The receipt must predate access to any target-month outcome. A missed deadline stays missed; retrospective reconstruction cannot count as issuance.

## Exclusions and outcome lock

Maintain a ledger for **all 12** scheduled months. Exclude a target for all models if the receipt is late or absent, a required input or provenance record is missing, invalid or nonfinite, VIX session coverage differs, or any model prediction is nonfinite. Document the reason. Keep input exclusions distinct from missing scoring outcomes. Never impute a missing input, replace an excluded month, change sources, or extend the panel based on losses.

For scoring, use the **ALFRED VIXCLS vintage dated 10 calendar days after the last calendar day of T**. Average daily VIX closes over the pinned sessions of T. Require an exact match of nonmissing target-month dates and finite values. Preserve the response hash and vintage date. If the vintage cannot be verified or coverage is incomplete, mark the outcome unscorable for all models. A later retrieval may recover only that exact vintage. Do not alter an issued prediction or substitute a later vintage. Lock forecasts before outcomes. Calculate aggregate results only once, after the final target's scoring vintage (December 10, 2027).

## Primary metric and decision

On the common set of issued months with verified outcomes, calculate equal-weight monthly **mean absolute error (MAE) in VIX points** for each model. The primary contrast is enhanced MAE minus controls MAE, equivalently the mean of the paired monthly absolute-error differences. A negative unrounded contrast favors adding GPR; zero is a tie. Publish all three MAEs, the signed contrast, the monthly loss pairs and the eligible count out of 12. Baseline comparisons, RMSE and MAPE are secondary and cannot override the primary contrast.

Require at least 9 common scored months for the directional conclusion. With 1–8 months, report descriptive scores and insufficient coverage; with zero months, report no score. This short panel supports a descriptive comparison and carries no significance or operational forecasting claim.

[Amendment A1, filed November 3, 2026](amendment-a1.md), governs receipt selection, outcome retry deadlines and the final status lock for all 12 targets.
