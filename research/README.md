# Month-end forecast reconstruction

The issue date is the end of the final VIX trading date in the month before the target, US Eastern time. Vintage evidence is daily. It does not establish an intraday trading signal. The outcome is the next calendar month's average daily VIX, scored against the repository's fixed outcome panel.

| Input | Observation and availability rule |
|---|---|
| VIX | Average the preceding month's daily VIX closes in the issue-date ALFRED snapshot. Check the set of available dates against the frozen trading calendar. |
| Brent | Average daily spot observations two calendar months before the target from the issue-date ALFRED snapshot. The extra lag allows the completed monthly window to be available. |
| Federal funds rate | Use the monthly effective rate two months before the target from that same vintage. |
| CPI inflation | Within that vintage, take the latest observed CPI reference month at least two months before the target and compare it with exactly 12 calendar months earlier. Record its reference month. A missing CPI stays missing. |
| Country GPR | Take the US, China, and Russia indices two months before the target from the publisher's workbook as committed on or before the issue date. A missing reference month excludes the row for all models. |
| Crisis controls | Keep the existing March–December 2020 and February–December 2022 windows fixed at model fitting. Both flags are zero throughout scoring. |

The pinned [VIX session calendar](vix_sessions.csv) contains only the 773 dates from December 2022 through November 2025 in Cboe's daily VIX history. The November 3, 2026 extract uses the DATE column alone, sorted and restricted to the 36 origin months. Its source-file SHA-256 is `2b76ef381fbff39fa7a500d4973d01952ccb47368a27b603b88e6bc78e990b42`. This retrospective session record determines both cutoffs and coverage. Later changes to VIX outcomes affect scoring only. [Cboe source CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)

ALFRED's vintage header confirms the as-of date for each series. The code also discards any observations dated after that cutoff. The source manifest records the four URLs, file hashes, and the GPR workbook's commit and Git committer timestamp (`gpr_committer_time_utc`) at each issue date. That timestamp serves as a publication proxy. The exact time the workbook first became publicly downloadable is unverified. GPR values may be revised after their initial release. [ALFRED](https://alfred.stlouisfed.org/) · [Caldara and Iacoviello GPR data and updates](https://www.matteoiacoviello.com/gpr.htm)

For October 2025 the CPI input is August. September CPI was released on October 24 and is available for the November forecast. With no October observation in the November-end vintage, December also uses September. November CPI was released December 18. [BLS September announcement](https://www.bls.gov/bls/092025-cpi-reschedule-notice.htm) · [BLS November release](https://www.bls.gov/news.release/archives/cpi_12182025.htm)

## Estimation and use

Fit three OLS models once using the first issue-date vintage (December 30, 2022). The historical training rows use information in that common fitting vintage, including revisions published by then. Each test row uses its own historical snapshot. All models use the same eligible training and evaluation rows. Model parameters and crisis windows stay fixed. Score actuals are added separately from predictors.

The monthly output records the cutoff, source periods, feature values, model predictions, signed errors, exclusions, and paired differences in absolute and squared error. A positive paired difference means adding country GPR increased loss. Interpret the 2023–2025 scores as a retrospective comparison on dates already inspected during development. No later outcomes are used for fitting or scoring.

## Reproduce

From the repository root, install the research requirements and run the script with an external cache directory. The committed source manifest pins downloads and verifies hashes. Creating the initial manifest also requires authenticated GitHub CLI access to resolve the publisher's historical file revisions.

```sh
python -m pip install -r research/requirements.txt
python research/forecast_origin.py --cache ../forecast-vintages
python -m pytest -q
```

Published files are under [outputs/forecast_origin](../outputs/forecast_origin).

## Results on the inspected 2023–2025 period

| Model | Training months | Scored months | MAE | RMSE | MAPE |
|---|---:|---:|---:|---:|---:|
| Prior VIX | 143 | 34 | 2.2403 | 3.1751 | 12.5733% |
| Prior VIX + macro and crisis controls | 143 | 34 | 2.5255 | 3.3865 | 14.9098% |
| Same controls + country GPR | 143 | 34 | 3.0966 | 4.0566 | 18.6550% |

All 36 scheduled targets are listed. October 2025 is eligible. The issue-date ALFRED snapshots for November and December lack the October 31 and November 28 VIX closes respectively, so the complete prior-month VIX predictor is unavailable from the selected archive. Both targets are excluded for every model. This is specific to the source used.

On the 33 dates shared with the earlier conditional backtest, baseline MAE is 2.25891925 in the earlier backtest and 2.25893528 in the forecast-date study. Both round to 2.2589 at four decimal places. Controls-only MAE rises from 1.9612 to 2.5624, and enhanced MAE rises from 2.0169 to 3.1785. Both input timing and vintage differ, so those changes cannot be assigned to any one series. The overall loss ranking on these inspected dates does not establish performance on future months.

The [prospective evaluation protocol](prospective/README.md) freezes the models and scoring rules for the December 2026 through November 2027 targets.
