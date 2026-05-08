# Geopolitical Risk and U.S. Market Volatility

## Project Overview

This project is a quantitative research study examining whether geopolitical risk involving the United States, China, and Russia helps explain or forecast U.S. stock market volatility. The project uses Python to clean, merge, analyze, visualize, and model monthly data from 2010 to 2025.

The main outcome variable is the **VIX**, a market-based measure of expected U.S. stock market volatility. The study compares global geopolitical risk, country-specific geopolitical risk, oil prices, inflation, interest rates, crisis-period controls, and forecasting models to evaluate whether geopolitical risk adds measurable explanatory or predictive value.

The final report finds that geopolitical risk alone does not consistently explain U.S. market volatility. While U.S.-specific geopolitical risk appears significant in simpler models, its effect disappears after controlling for lagged VIX and major crisis periods. The strongest predictors in the enhanced models are prior-month VIX, inflation, and the COVID-period dummy variable.

## Key Research Question

Does geopolitical risk involving the United States, China, and Russia significantly affect U.S. stock market volatility, and does it improve volatility forecasting compared with a simple lagged-VIX benchmark?

## Key Findings

1. The global Geopolitical Risk Index is not a statistically significant predictor of monthly VIX in the baseline Brent or WTI models.
2. Country-specific U.S. geopolitical risk appears significant in simpler and lagged models, but the coefficient is negative and weakens after stronger controls are added.
3. Enhanced regression models explain substantially more variation in VIX, with R-squared values near 0.60.
4. After controlling for lagged VIX, inflation, oil prices, interest rates, and crisis periods, lagged U.S.-specific GPR is no longer statistically significant.
5. The forecasting backtest shows that the enhanced model improves MAE and MAPE relative to a lagged-VIX benchmark, but performs worse by RMSE, indicating that sudden volatility spikes remain difficult to predict.

## Data Sources

The project uses publicly available economic, financial, and geopolitical datasets.

| Data | Source | Purpose |
|---|---|---|
| VIX | Federal Reserve Economic Data (FRED) | Dependent variable measuring U.S. market volatility |
| Global GPR Index | Caldara and Iacoviello Geopolitical Risk Index | Measures broad geopolitical risk |
| Country-specific GPR indexes | Caldara and Iacoviello Geopolitical Risk Index | Measures geopolitical risk associated with the U.S., China, and Russia |
| Brent crude oil prices | FRED | Global oil-price control |
| WTI crude oil prices | FRED | U.S.-focused oil-price robustness check |
| CPI | FRED | Used to calculate year-over-year inflation |
| Federal Funds Rate | FRED | Monetary-policy control |
| World Economic Forum Global Risks Report 2026 | WEF | Current geopolitical and geoeconomic context |
| 2026 Annual Threat Assessment | Office of the Director of National Intelligence | Current major-power competition context |
| IMF World Economic Outlook, April 2026 | IMF | Current macroeconomic and geopolitical-risk context |

## Variables Used

### Dependent Variable

- **VIX**: Measures expected U.S. stock market volatility. Higher VIX values indicate greater expected market uncertainty.

### Main Geopolitical Variables

- **Global GPR**: Broad global geopolitical risk index.
- **U.S. GPR**: Country-specific geopolitical risk associated with the United States.
- **China GPR**: Country-specific geopolitical risk associated with China.
- **Russia GPR**: Country-specific geopolitical risk associated with Russia.

### Control Variables

- **Brent crude oil price**: Global benchmark for oil-market conditions.
- **WTI crude oil price**: U.S.-focused oil benchmark used as a robustness check.
- **Inflation rate**: Year-over-year CPI inflation.
- **Federal Funds Rate**: U.S. monetary-policy indicator.
- **Lagged VIX**: One-month lag of VIX, used to control for volatility persistence.
- **COVID-period dummy**: Indicator variable for the COVID crisis period.
- **Russia-Ukraine war-period dummy**: Indicator variable for the Russia-Ukraine war period.

## Methodology

The project follows a staged quantitative modeling approach:

1. **Data collection and cleaning**
   - Downloaded raw data from FRED and the GPR dataset.
   - Converted daily series into monthly averages.
   - Calculated year-over-year inflation from CPI.
   - Merged all variables into a single monthly dataset.

2. **Descriptive analysis**
   - Plotted VIX, global GPR, country-specific GPR, oil prices, inflation, and interest rates.
   - Created a correlation heatmap to evaluate relationships among variables.

3. **Regression analysis**
   - Estimated baseline OLS models using global GPR.
   - Estimated country-specific GPR models.
   - Estimated lagged country-specific GPR models.
   - Estimated enhanced models with lagged VIX and crisis-period controls.

4. **Forecasting and backtesting**
   - Trained models on pre-2023 monthly data.
   - Tested forecasts on the 2023–2025 holdout period.
   - Compared a baseline lagged-VIX model against an enhanced model using geopolitical and macroeconomic variables.
   - Evaluated forecast performance using MAE, RMSE, and MAPE.

## Forecasting Results

The forecasting backtest compares two models:

| Model | MAE | RMSE | MAPE |
|---|---:|---:|---:|
| Baseline: Lagged VIX Only | 2.3357 | 3.2348 | 13.1513% |
| Enhanced: GPR + Macro + Crisis Controls | 2.0976 | 3.3717 | 10.8721% |

The enhanced model improves average forecast accuracy by MAE and MAPE, but performs worse by RMSE. This suggests that geopolitical and macroeconomic variables help during typical months but do not fully capture sudden volatility spikes.

## Main Outputs

The project produces the following outputs:

```text
outputs/
├── geopolitical_risk_quantitative_report.pdf
├── regression_results_summary.xlsx
├── forecast_accuracy_summary.xlsx
├── forecast_backtest_results.xlsx
├── forecast_backtest_results.csv
└── charts/
    ├── actual_vs_predicted_vix_forecast.png
    ├── correlation_heatmap.png
    ├── country_gpr_over_time.png
    ├── forecast_errors_over_time.png
    ├── global_gpr_over_time.png
    ├── inflation_and_fedfunds_over_time.png
    ├── lagged_us_gpr_vs_vix.png
    ├── oil_prices_over_time.png
    ├── vix_and_lagged_vix_over_time.png
    ├── vix_crisis_periods_highlighted.png
    └── vix_over_time.png
```

## Project Structure

```text
geopolitical-risk-project/
├── data_raw/
│   ├── cpi.csv
│   ├── fed_funds_rate.csv
│   ├── gpr_index.xls
│   ├── oil_brent.csv
│   ├── oil_wti.csv
│   └── vix.csv
├── data_clean/
│   ├── merged_monthly_data.csv
│   └── merged_monthly_data.xlsx
├── outputs/
│   ├── charts/
│   ├── geopolitical_risk_quantitative_report.pdf
│   ├── regression_results_summary.xlsx
│   ├── forecast_accuracy_summary.xlsx
│   ├── forecast_backtest_results.xlsx
│   └── forecast_backtest_results.csv
├── geopolitical_risk_analysis.ipynb
├── create_pdf_report.py
└── README.md
```

## Tools and Libraries

This project was completed in Python using:

- pandas
- numpy
- matplotlib
- statsmodels
- openpyxl
- reportlab
- pathlib

## How to Run the Project

1. Clone or download the project folder.
2. Create and activate a Python virtual environment.
3. Install required packages:

```bash
pip install pandas numpy matplotlib statsmodels openpyxl reportlab
```

4. Run the Jupyter Notebook:

```text
geopolitical_risk_analysis.ipynb
```

5. Generate the final PDF report:

```bash
python create_pdf_report.py
```

The final PDF will be saved to:

```text
outputs/geopolitical_risk_quantitative_report.pdf
```

## Interpretation

The results suggest that geopolitical risk has a conditional rather than automatic relationship with U.S. market volatility. Broad global geopolitical risk is not a reliable standalone predictor of VIX. Country-specific U.S. geopolitical risk appears more relevant in simpler models, but its statistical significance disappears after accounting for lagged volatility and crisis-period shocks.

The enhanced models show that volatility persistence, inflation, and crisis shocks explain more variation in monthly VIX than geopolitical risk alone. The forecasting results also show that adding geopolitical and macroeconomic variables can improve average forecast accuracy, but sudden volatility spikes remain difficult to predict.

## Limitations

- The study uses monthly data, which may miss short-term market reactions to geopolitical events.
- Several GPR variables are highly correlated, creating potential multicollinearity.
- The model does not include all possible macro-financial controls, such as unemployment, credit spreads, exchange rates, or equity returns.
- The forecasting backtest uses known historical values for explanatory variables during the test period. A true forward-looking forecast would require future assumptions about inflation, interest rates, oil prices, geopolitical risk, and crisis conditions.

## Future Improvements

Potential future extensions include:

- Using daily data for an event-study design.
- Adding equity returns, credit spreads, exchange rates, or financial stress indexes.
- Testing nonlinear models or machine learning forecasting methods.
- Creating a dashboard version of the project.
- Building scenario forecasts for geopolitical shock, macro stress, and combined risk environments.

## Portfolio Summary

This project demonstrates skills in:

- quantitative research
- financial risk analysis
- geopolitical risk analysis
- Python data cleaning
- time-series data preparation
- regression modeling
- forecasting and backtesting
- data visualization
- automated PDF report generation
- communicating analytical findings for a business audience

## Disclaimer

This project is for educational and portfolio purposes only. It is not investment advice, financial advice, or a trading model.
