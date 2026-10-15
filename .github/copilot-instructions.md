# Copilot instructions: Geopolitical Risk and U.S. Market Volatility

## Purpose
Python-based quantitative study analyzing whether U.S., China, and Russia geopolitical risk explains or forecasts U.S. market volatility using VIX, GPR indexes, macroeconomic controls, regression modeling, and forecasting backtesting.

## Tech stack
- Python (no dependency file committed; infer imports from source)
- Imports observed: `pandas`, `reportlab`

## Folder structure
- `data_clean/` (2 files)
- `data_raw/` (6 files)
- `outputs/` (16 files)
- `README.md`
- `create_pdf_report.py`
- `geopolitical_risk_analysis.ipynb`

## Setup, run, test
Commands documented in README.md (referenced files exist):
```bash
pip install pandas numpy matplotlib statsmodels openpyxl reportlab
python create_pdf_report.py
```
- No automated tests exist yet; if adding them, use pytest under `tests/`.

## Conventions observed
- Public data sources referenced: FRED.
- Write paths relative to the repo root (no absolute local paths).

## Output artifacts
- Generated outputs go to: `outputs/charts/`
- A PDF report is produced with `reportlab`; keep it in sync with model changes.

## Guardrails
- Never commit secrets, API keys, tokens, or `.env` files.
- Do not commit large raw datasets or binaries; keep data fetched or documented with its source.
- Keep analysis source-backed: cite data sources and assumptions; label scenario/forecast outputs as model estimates, not facts.
- Preserve reproducibility: no unseeded randomness, no hidden manual steps.
