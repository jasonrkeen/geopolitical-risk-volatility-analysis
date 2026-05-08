from pathlib import Path
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    Table,
    TableStyle,
    KeepTogether,
)

# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------
BASE_DIR = Path.cwd()
OUTPUTS_DIR = BASE_DIR / "outputs"
CHARTS_DIR = OUTPUTS_DIR / "charts"
PDF_PATH = OUTPUTS_DIR / "geopolitical_risk_quantitative_report.pdf"

# Create folders if they do not already exist
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# Load output tables
# ------------------------------------------------------------
regression_path = OUTPUTS_DIR / "regression_results_summary.xlsx"
forecast_accuracy_path = OUTPUTS_DIR / "forecast_accuracy_summary.xlsx"

if not regression_path.exists():
    raise FileNotFoundError(
        f"Missing regression table: {regression_path}\n"
        "Make sure regression_results_summary.xlsx is saved in the outputs folder."
    )

regression_table = pd.read_excel(regression_path, index_col=0).round(4)

forecast_accuracy_table = None
if forecast_accuracy_path.exists():
    forecast_accuracy_table = pd.read_excel(forecast_accuracy_path).round(4)
else:
    print(f"Warning: Missing forecast accuracy table: {forecast_accuracy_path}")

# ------------------------------------------------------------
# Styles
# ------------------------------------------------------------
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleStyle",
    parent=styles["Title"],
    fontSize=18,
    leading=22,
    alignment=TA_CENTER,
    spaceAfter=18,
)

subtitle_style = ParagraphStyle(
    "SubtitleStyle",
    parent=styles["Heading2"],
    fontSize=12,
    leading=15,
    alignment=TA_CENTER,
    spaceBefore=4,
    spaceAfter=12,
)

heading_style = ParagraphStyle(
    "HeadingStyle",
    parent=styles["Heading1"],
    fontSize=14,
    leading=18,
    spaceBefore=10,
    spaceAfter=7,
)

subheading_style = ParagraphStyle(
    "SubheadingStyle",
    parent=styles["Heading2"],
    fontSize=11.5,
    leading=14,
    spaceBefore=8,
    spaceAfter=5,
)

body_style = ParagraphStyle(
    "BodyStyle",
    parent=styles["BodyText"],
    fontSize=9.6,
    leading=13.1,
    alignment=TA_LEFT,
    spaceAfter=7,
)

caption_style = ParagraphStyle(
    "CaptionStyle",
    parent=styles["BodyText"],
    fontSize=7.35,
    leading=9.0,
    italic=True,
    textColor=colors.darkgrey,
    spaceBefore=2,
    spaceAfter=5,
)

small_style = ParagraphStyle(
    "SmallStyle",
    parent=styles["BodyText"],
    fontSize=8.0,
    leading=10,
    alignment=TA_LEFT,
    spaceAfter=5,
)

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def add_chart(story, filename, caption, width=5.75 * inch):
    """
    Adds a chart and its caption as a single grouped block.
    The smaller default width and KeepTogether wrapper reduce blank pages
    and prevent captions from being separated from their charts.
    """
    chart_path = CHARTS_DIR / filename

    if not chart_path.exists():
        story.append(Paragraph(f"[Missing chart: {filename}]", body_style))
        return

    img = Image(str(chart_path))
    scale = width / img.drawWidth
    img.drawWidth = width
    img.drawHeight = img.drawHeight * scale

    chart_block = [
        img,
        Paragraph(caption, caption_style),
        Spacer(1, 0.035 * inch),
    ]

    story.append(KeepTogether(chart_block))


def dataframe_to_reportlab_table(df, font_size=6.1):
    display_df = df.copy().astype(str)
    table_data = [["Metric"] + list(display_df.columns)]

    for idx, row in display_df.iterrows():
        table_data.append([str(idx)] + list(row.values))

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    return table


def simple_dataframe_to_reportlab_table(df, font_size=8):
    display_df = df.copy().astype(str)
    table_data = [list(display_df.columns)]

    for _, row in display_df.iterrows():
        table_data.append(list(row.values))

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    return table


def add_key_finding(story, number, text):
    story.append(
        Paragraph(
            f"<b>{number}.</b> {text}",
            body_style,
        )
    )


def page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(7.5 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


# ------------------------------------------------------------
# Split regression tables for cleaner display
# ------------------------------------------------------------
original_model_columns = [
    "Global GPR + Brent",
    "Global GPR + WTI",
    "Country GPR + Brent",
    "Country GPR + WTI",
    "Lagged Country GPR + Brent",
    "Lagged Country GPR + WTI",
]

enhanced_model_columns = [
    "Enhanced Model + Brent",
    "Enhanced Model + WTI",
]

original_regression_table = regression_table[
    [col for col in original_model_columns if col in regression_table.columns]
]

enhanced_regression_table = regression_table[
    [col for col in enhanced_model_columns if col in regression_table.columns]
]

# ------------------------------------------------------------
# Build PDF
# ------------------------------------------------------------
doc = SimpleDocTemplate(
    str(PDF_PATH),
    pagesize=letter,
    rightMargin=0.55 * inch,
    leftMargin=0.55 * inch,
    topMargin=0.55 * inch,
    bottomMargin=0.55 * inch,
)

story = []

# ------------------------------------------------------------
# Title page
# ------------------------------------------------------------
story.append(
    Paragraph(
        "The Quantitative Impact of U.S., China, and Russia Geopolitical Risk on Market Volatility",
        title_style,
    )
)
story.append(Paragraph("Quantitative Research Report", subtitle_style))
story.append(Spacer(1, 0.15 * inch))

story.append(
    Paragraph(
        "This report examines whether geopolitical risk involving the United States, China, and Russia is associated with changes in U.S. financial market volatility. The study uses monthly data from 2010 to 2025 to connect geopolitical risk, financial-market volatility, energy prices, inflation, and interest-rate conditions in one quantitative framework.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The core variables are the VIX, which represents U.S. stock market volatility; the global and country-specific Geopolitical Risk Index variables, which represent geopolitical risk exposure; Brent and WTI crude oil prices, which capture energy-market conditions; the year-over-year CPI inflation rate, which captures price pressure; and the Federal Funds Rate, which captures the monetary-policy environment. These variables were selected because geopolitical shocks often affect markets through uncertainty, energy costs, inflation expectations, and policy responses.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The analysis compares baseline geopolitical-risk regressions, country-specific models, lagged models, enhanced models with crisis-period controls, and a forecasting backtest. The goal is not to claim that geopolitics alone predicts market volatility, but to test whether geopolitical information adds measurable explanatory or predictive value once macroeconomic conditions are included. The report also connects the quantitative results to current risk frameworks from the World Economic Forum, the U.S. Annual Threat Assessment, and the International Monetary Fund.",
        body_style,
    )
)

story.append(PageBreak())

# ------------------------------------------------------------
# 1. Introduction
# ------------------------------------------------------------
story.append(Paragraph("1. Introduction", heading_style))

story.append(
    Paragraph(
        "Geopolitical risk has become a central issue for businesses, investors, policymakers, and risk managers. Strategic competition among the United States, China, and Russia affects the global economy through sanctions, military conflict, supply-chain restrictions, energy-market instability, cyber risk, export controls, and uncertainty about future policy. These risks are not only political; they can influence the cost of capital, investor sentiment, commodity prices, inflation expectations, and the willingness of firms to invest across borders.",
        body_style,
    )
)

story.append(
    Paragraph(
        "Recent global-risk assessments support the importance of this topic. The World Economic Forum's Global Risks Report 2026 describes an environment of rising fragmentation and identifies geoeconomic confrontation as a leading short-term global risk. The 2026 Annual Threat Assessment of the U.S. Intelligence Community emphasizes major-power competition, economic fragmentation, competition over supply chains and technological primacy, and unresolved regional conflicts as interconnected risks. The IMF's April 2026 World Economic Outlook also frames the global economy as operating in the shadow of war, where geopolitical tensions interact with energy markets, inflation, supply chains, financial conditions, and uncertainty. Together, these sources make geopolitical risk a relevant subject for quantitative financial analysis rather than only a foreign-policy issue.",
        body_style,
    )
)

story.append(
    Paragraph(
        "This project focuses on whether geopolitical risk is reflected in U.S. financial-market volatility. The dependent variable is the VIX, which is commonly used as a market-based measure of expected stock-market volatility. The main explanatory variables are the global Geopolitical Risk Index and country-specific GPR indexes for the United States, China, and Russia. The study also includes Brent and WTI crude oil prices, inflation, and the Federal Funds Rate because geopolitical risk can affect markets indirectly through energy shocks, price pressure, and monetary-policy conditions.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The main research question is: Does geopolitical risk involving the United States, China, and Russia significantly affect U.S. stock market volatility, and does it improve the ability to forecast volatility compared with a simple lagged-VIX benchmark? This question matters because market participants rarely experience geopolitical risk as an isolated political event. Instead, geopolitical pressure often appears through oil-price volatility, inflation expectations, interest-rate responses, trade restrictions, supply-chain uncertainty, cyber and technology risk, and flight-to-safety behavior.",
        body_style,
    )
)

# ------------------------------------------------------------
# 2. Key Findings
# ------------------------------------------------------------
story.append(Paragraph("2. Key Findings", heading_style))

add_key_finding(
    story,
    1,
    "The global GPR index is not a statistically significant predictor of monthly VIX in the baseline Brent or WTI models, suggesting that broad geopolitical risk is too general to explain U.S. market volatility on its own.",
)
add_key_finding(
    story,
    2,
    "Country-specific U.S. geopolitical risk appears significant in simpler and lagged models, but the coefficient is negative and the result weakens once more rigorous controls are added.",
)
add_key_finding(
    story,
    3,
    "The enhanced models explain much more of the variation in VIX, with R-squared values near 0.60, mainly because they include lagged VIX and crisis-period controls.",
)
add_key_finding(
    story,
    4,
    "After controlling for lagged VIX, inflation, oil prices, interest rates, and crisis periods, lagged U.S.-specific GPR is no longer statistically significant.",
)
add_key_finding(
    story,
    5,
    "The forecasting backtest shows that the enhanced model improves MAE and MAPE relative to a lagged-VIX benchmark, but performs worse by RMSE, meaning sudden volatility spikes remain difficult to predict.",
)

# ------------------------------------------------------------
# 3. Hypotheses
# ------------------------------------------------------------
story.append(Paragraph("3. Hypotheses", heading_style))

story.append(
    Paragraph(
        "The hypotheses are organized around a progression from simple explanation to more demanding predictive testing. The first expectation is that higher global geopolitical risk should be associated with higher U.S. stock-market volatility because uncertainty about conflict, sanctions, trade restrictions, and energy markets can increase investor concern. This is the basic relationship tested in the global GPR models.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The second expectation is that country-specific geopolitical risk for the United States, China, and Russia may explain market volatility better than the broad global index. This is important because the global index may combine many geopolitical events that are not equally relevant to U.S. financial markets. By separating U.S., China, and Russia risk, the model can test whether the source of geopolitical risk matters.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The third expectation is that lagged geopolitical risk may have greater explanatory power than same-month geopolitical risk. Financial markets often respond quickly to events, but monthly data may capture delayed effects, policy responses, or persistent uncertainty. The lagged models therefore test whether geopolitical risk in one month helps explain VIX in the following month.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The fourth expectation is more demanding: geopolitical risk should remain statistically significant after controlling for lagged VIX and major crisis periods. This tests whether geopolitical risk adds information beyond volatility persistence and extraordinary shocks such as COVID-19 or the Russia-Ukraine war period.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The final expectation is predictive. If geopolitical and macroeconomic variables contain useful forward-looking information, an enhanced forecasting model should perform better than a baseline model that uses only one-month lagged VIX. The forecasting backtest evaluates this using MAE, RMSE, and MAPE during the 2023-2025 holdout period.",
        body_style,
    )
)

# ------------------------------------------------------------
# 4. Data and Methodology
# ------------------------------------------------------------
story.append(Paragraph("4. Data and Methodology", heading_style))

story.append(
    Paragraph(
        "The study uses monthly observations from 2010 to 2025. This period captures several major sources of economic and geopolitical stress, including the post-financial-crisis recovery, U.S.-China trade tensions, the COVID-19 shock, Russia's invasion of Ukraine, energy-price volatility, rapid inflation, and the sharp increase in U.S. interest rates after 2021. Daily variables such as the VIX and crude oil prices were converted to monthly averages so that they could be aligned with the monthly geopolitical risk and macroeconomic data.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The variable selection follows the transmission channels emphasized in current global-risk research. The WEF highlights geoeconomic confrontation and fragmentation, ODNI highlights major-power competition and supply-chain and technology competition, and the IMF highlights how geopolitical tensions can affect commodity prices, supply chains, inflation, exchange rates, and financial conditions. For this reason, the study includes not only GPR indexes, but also oil prices, inflation, interest rates, lagged volatility, and crisis-period controls.",
        body_style,
    )
)

story.append(Paragraph("4.1 Variable Definitions", subheading_style))

story.append(
    Paragraph(
        "The dependent variable is the VIX. It was chosen because it is a widely used measure of expected U.S. equity-market volatility and is often interpreted as a market fear or uncertainty gauge. A higher VIX indicates that investors expect larger stock-market movements, making it appropriate for testing whether geopolitical risk is reflected in financial-market stress.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The main geopolitical variables are the global GPR index and the country-specific GPR indexes for the United States, China, and Russia. The global index measures broad geopolitical risk, while the country-specific indexes allow the study to test whether risks associated with particular major powers have different relationships with U.S. volatility. This distinction matters because a global geopolitical event may not affect U.S. markets in the same way as an event directly connected to the United States, China, or Russia.",
        body_style,
    )
)

story.append(
    Paragraph(
        "Brent and WTI crude oil prices are included because geopolitical conflict often affects markets through energy channels. Brent is treated as the primary oil-market control because it is a global benchmark, while WTI is included as a U.S.-focused robustness check. If the results are similar under both oil benchmarks, the findings are less likely to depend on the choice of oil price measure.",
        body_style,
    )
)

story.append(
    Paragraph(
        "Inflation is measured using the year-over-year change in CPI. It was chosen because inflation affects interest-rate expectations, consumer purchasing power, corporate costs, and investor uncertainty. The Federal Funds Rate is included to represent monetary-policy conditions. Higher interest rates can influence equity valuations and risk appetite, so controlling for the policy environment is important when studying the VIX.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The enhanced models also include one-month lagged VIX, a COVID-period dummy variable, and a Russia-Ukraine war-period dummy variable. Lagged VIX controls for volatility persistence, meaning that high-volatility months tend to be followed by elevated volatility in the next month. The crisis-period dummies help separate broad geopolitical-risk effects from extraordinary shocks that may dominate the VIX during specific periods.",
        body_style,
    )
)

story.append(Paragraph("4.2 Model Strategy", subheading_style))

story.append(
    Paragraph(
        "The analysis begins with ordinary least squares regression models using global GPR, oil prices, inflation, and the Federal Funds Rate. It then moves to country-specific models, followed by lagged country-specific models. The final explanatory models add lagged VIX and crisis-period controls to test whether the geopolitical risk relationship remains after accounting for volatility persistence and major shocks.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The forecasting section uses a historical backtest. Models are trained on pre-2023 monthly data and tested on the 2023-2025 holdout period. The baseline forecast model uses only lagged VIX. The enhanced forecast model uses lagged VIX, country-specific geopolitical risk, oil prices, inflation, interest rates, and crisis-period controls. Forecast accuracy is evaluated using mean absolute error, root mean squared error, and mean absolute percentage error.",
        body_style,
    )
)

# ------------------------------------------------------------
# 5. Descriptive Charts
# ------------------------------------------------------------
story.append(Paragraph("5. Descriptive Charts", heading_style))

story.append(
    Paragraph(
        "The charts provide the visual foundation for the statistical analysis. They show that VIX spikes are concentrated in specific periods, that global and country-specific geopolitical risk rose sharply around 2022, and that inflation, interest rates, and oil prices also changed meaningfully during the sample. These patterns support the use of both geopolitical variables and macro-financial controls in the regression and forecasting models.",
        body_style,
    )
)

# No manual page breaks inside this chart section. ReportLab will paginate the
# grouped chart blocks automatically, which helps avoid blank pages.
add_chart(
    story,
    "vix_over_time.png",
    "Figure 1. VIX over time, 2010-2025. The chart shows that market volatility is episodic rather than constant. The largest spike occurs in 2020, while additional increases appear around 2011-2012, 2022, and 2025. This pattern suggests that volatility is strongly affected by crisis periods and supports the later use of lagged VIX and crisis controls.",
)

add_chart(
    story,
    "global_gpr_over_time.png",
    "Figure 2. Global Geopolitical Risk Index over time, 2010-2025. Global GPR rises sharply in 2022 and remains elevated afterward, consistent with a more persistent geopolitical-risk environment following the Russia-Ukraine war period. The chart also shows that geopolitical risk does not always move at the same time as the VIX, motivating the regression tests.",
)

add_chart(
    story,
    "country_gpr_over_time.png",
    "Figure 3. Country-specific geopolitical risk indices for the United States, China, and Russia. Russia-specific risk spikes sharply in 2022, while U.S.-specific risk also rises during the same period. China-specific GPR remains lower but gradually increases in several parts of the sample. This supports testing country-specific indexes rather than relying only on the global GPR measure.",
)

add_chart(
    story,
    "oil_prices_over_time.png",
    "Figure 4. Brent and WTI crude oil prices. The two benchmarks move closely together, but Brent is generally the more global measure while WTI is more U.S.-focused. Oil prices fall sharply around 2015-2016 and 2020 and rise again around 2022, showing why energy conditions should be controlled for when analyzing market volatility.",
)

add_chart(
    story,
    "inflation_and_fedfunds_over_time.png",
    "Figure 5. Inflation and the Federal Funds Rate. Inflation rises sharply beginning in 2021, followed by a rapid increase in the Federal Funds Rate. This chart helps explain why inflation and interest rates are included in the models: macroeconomic stress and monetary policy can affect the VIX independently of geopolitical risk.",
)

add_chart(
    story,
    "correlation_heatmap.png",
    "Figure 6. Correlation heatmap of the main study variables. VIX has weak direct correlations with the GPR variables, while the GPR variables are highly correlated with each other. This suggests that the direct relationship between geopolitical risk and volatility may be limited and that multicollinearity should be considered when interpreting country-specific models.",
)

story.append(
    KeepTogether(
        [
            Paragraph(
                "Taken together, the descriptive charts show that market volatility, geopolitical risk, energy prices, inflation, and interest rates each experienced major changes during the sample period, but they did not move in identical patterns. This is why regression modeling is necessary: the visual evidence suggests relationships worth testing, but it does not by itself prove whether geopolitical risk has an independent effect on market volatility.",
                body_style,
            ),
            Spacer(1, 0.04 * inch),
        ]
    )
)

add_chart(
    story,
    "vix_and_lagged_vix_over_time.png",
    "Figure 7. Current VIX and one-month lagged VIX over time. The close movement between the two series shows that volatility is persistent. This is important because a model that ignores lagged VIX may incorrectly attribute persistent volatility to geopolitical or macroeconomic variables.",
)

add_chart(
    story,
    "vix_crisis_periods_highlighted.png",
    "Figure 8. VIX with COVID and Russia-Ukraine war periods highlighted. The COVID period overlaps with the largest volatility spike in the sample, while the Russia-Ukraine period coincides with elevated but less extreme volatility. This supports including crisis-period dummy variables in the enhanced models.",
)

story.append(PageBreak())

# ------------------------------------------------------------
# 6. Regression Results
# ------------------------------------------------------------
story.append(Paragraph("6. Regression Results", heading_style))

story.append(
    Paragraph(
        "The regression results are presented in stages so that the effect of adding additional controls can be seen clearly. Table 1 reports the initial models. The first two models use the global GPR index with Brent and WTI oil controls. In both cases, the global GPR coefficient is small and statistically insignificant, meaning the broad global risk index does not explain VIX in a reliable way after accounting for oil prices, inflation, and interest rates.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The next models separate geopolitical risk into U.S., China, and Russia-specific indexes. In these simpler country-specific models, U.S.-specific GPR becomes statistically significant or nearly significant, and the lagged country-specific models produce the strongest initial GPR result. This suggests that country-specific GPR contains more relevant information than the broad global index. However, the coefficient is negative rather than positive, which indicates that the relationship is not as straightforward as the original hypothesis predicted.",
        body_style,
    )
)

if not original_regression_table.empty:
    story.append(dataframe_to_reportlab_table(original_regression_table, font_size=5.95))
    story.append(
        Paragraph(
            "Table 1. Initial regression results. The key GPR coefficient refers to global GPR in the global models and U.S.-specific GPR in the country and lagged country models.",
            caption_style,
        )
    )
else:
    story.append(Paragraph("[Original regression table columns were not found in regression_results_summary.xlsx.]", body_style))

story.append(
    Paragraph(
        "In the global GPR models, the key GPR coefficient is negative and not statistically significant, which means the broad global risk index does not explain monthly VIX movements after the macro controls are included. In the country-specific and lagged models, U.S.-specific GPR becomes statistically significant or nearly significant, but the coefficient remains negative. This unexpected sign is important because it shows why the project should not stop at the simpler models; the relationship needs to be tested against volatility persistence and crisis-period effects.",
        body_style,
    )
)

story.append(
    Paragraph(
        "Table 2 presents the enhanced models, which are the most rigorous explanatory specifications in the report. These models add lagged VIX, a COVID-period dummy, and a Russia-Ukraine war-period dummy. After these controls are added, lagged U.S.-specific GPR is no longer statistically significant. This means that the apparent GPR effect in the simpler models is largely absorbed by volatility persistence and crisis-period effects.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The increase in R-squared to approximately 0.60 is important. It shows that the enhanced model explains far more of the variation in VIX than the simpler geopolitical-risk models. The interpretation is not that geopolitics is irrelevant; rather, the evidence suggests that its effect is conditional and difficult to isolate once broader market dynamics and crisis periods are considered.",
        body_style,
    )
)

if not enhanced_regression_table.empty:
    story.append(dataframe_to_reportlab_table(enhanced_regression_table, font_size=7.0))
    story.append(
        Paragraph(
            "Table 2. Enhanced regression results. The enhanced models use lagged U.S.-specific GPR as the key GPR variable and control for lagged VIX, crisis periods, inflation, interest rates, and oil prices.",
            caption_style,
        )
    )
else:
    story.append(Paragraph("[Enhanced regression table columns were not found in regression_results_summary.xlsx.]", body_style))

story.append(PageBreak())

add_chart(
    story,
    "lagged_us_gpr_vs_vix.png",
    "Figure 9. Lagged U.S. GPR versus VIX. The fitted line slopes slightly downward, consistent with the simpler lagged regression models. However, the scatter is wide, showing that lagged U.S. GPR alone does not explain most variation in VIX. This visual pattern is consistent with the enhanced models, where the GPR effect weakens after adding lagged VIX and crisis controls.",
)

# ------------------------------------------------------------
# 7. Forecasting and Backtesting
# ------------------------------------------------------------
story.append(Paragraph("7. Forecasting and Backtesting", heading_style))

story.append(
    Paragraph(
        "To extend the study from explanation to prediction, a forecasting backtest was conducted for the 2023-2025 period. The forecasting exercise compares a simple baseline model using only one-month lagged VIX with an enhanced model that includes lagged VIX, geopolitical risk variables, oil prices, inflation, interest rates, and crisis-period controls.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The purpose of the backtest is to evaluate whether geopolitical and macroeconomic variables improve predictive performance beyond a simple volatility-persistence benchmark. This is important for a portfolio project because it tests whether the model has practical predictive value, not just explanatory value within the historical sample.",
        body_style,
    )
)

if forecast_accuracy_table is not None:
    story.append(simple_dataframe_to_reportlab_table(forecast_accuracy_table, font_size=8.0))
    story.append(
        Paragraph(
            "Table 3. Forecast accuracy results for the 2023-2025 backtest. Lower values indicate better forecast accuracy.",
            caption_style,
        )
    )
else:
    story.append(Paragraph("[Forecast accuracy table not found. Run the forecasting section of the notebook first.]", body_style))

add_chart(
    story,
    "actual_vs_predicted_vix_forecast.png",
    "Figure 10. Actual versus predicted VIX forecasts for 2023-2025. The chart compares the baseline lagged-VIX forecast with the enhanced model forecast. Both models follow the general level of VIX, but both struggle with sudden spikes. This illustrates a key challenge in volatility forecasting: extreme events are difficult to predict using monthly explanatory variables.",
)

add_chart(
    story,
    "forecast_errors_over_time.png",
    "Figure 11. Forecast errors over time for 2023-2025. Forecast errors are calculated as actual VIX minus predicted VIX. The largest errors occur around the largest volatility movement in the test period, showing that the models are more effective during normal months than during abrupt volatility shocks.",
)

story.append(
    Paragraph(
        "The enhanced model improves average predictive accuracy relative to the baseline model, as shown by lower MAE and MAPE. However, the enhanced model has a slightly higher RMSE, suggesting that it may perform worse during large volatility spikes. This indicates that geopolitical and macroeconomic variables can improve typical monthly forecasts but still do not fully capture sudden volatility shocks.",
        body_style,
    )
)

story.append(PageBreak())

# ------------------------------------------------------------
# 8. Discussion
# ------------------------------------------------------------
story.append(Paragraph("8. Discussion", heading_style))

story.append(
    Paragraph(
        "The results do not support the initial expectation that geopolitical risk uniformly increases U.S. market volatility. The global GPR index was not a statistically significant predictor of the VIX after controlling for oil prices, inflation, and interest rates. This suggests that broad geopolitical risk may be too general to explain month-to-month movements in U.S. market volatility.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The country-specific models provide a more nuanced result. In the simpler country-specific and lagged models, U.S.-specific geopolitical risk is statistically significant or close to statistically significant. However, the sign of the coefficient is negative, meaning that higher U.S.-specific GPR is associated with lower VIX in those specifications. This unexpected direction suggests that the relationship between geopolitical risk and market volatility is more complex than the original hypothesis predicted.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The enhanced models provide the most important finding. Once lagged VIX and crisis-period controls are added, U.S.-specific geopolitical risk is no longer statistically significant. This indicates that the earlier GPR result was likely influenced by volatility persistence and major crisis-period shocks. The strongest predictors of current VIX in the enhanced models are prior-month VIX, inflation, and the COVID-period dummy variable.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The COVID-period dummy is positive and statistically significant in both enhanced models, showing that the pandemic period had a large independent effect on market volatility. By contrast, the Russia-Ukraine war-period dummy is positive but not statistically significant in the enhanced models. This suggests that, within this monthly VIX framework, the COVID shock had a clearer effect on U.S. market volatility than the Ukraine war period after other variables were controlled.",
        body_style,
    )
)

story.append(
    Paragraph(
        "The forecasting backtest adds a predictive perspective to the analysis. The enhanced model performs better than the baseline model by MAE and MAPE, suggesting that macroeconomic and geopolitical variables improve average forecast accuracy. However, the higher RMSE shows that large volatility spikes remain difficult to forecast.",
        body_style,
    )
)

story.append(
    Paragraph(
        "Overall, the enhanced results suggest that U.S. market volatility from 2010 to 2025 was driven more strongly by volatility persistence, inflation, and crisis-specific shocks than by geopolitical risk measures alone.",
        body_style,
    )
)

# ------------------------------------------------------------
# 9. Hypothesis Evaluation
# ------------------------------------------------------------
story.append(Paragraph("9. Hypothesis Evaluation", heading_style))

story.append(Paragraph("H1 is not supported. The global GPR index is not statistically significant in the global Brent or WTI models.", body_style))
story.append(Paragraph("H2 is partially supported in the simpler models because country-specific U.S. GPR performs better than global GPR. However, this support weakens in the enhanced models.", body_style))
story.append(Paragraph("H3 is partially supported in the simpler lagged models because lagged U.S. GPR is statistically significant. However, the relationship disappears after lagged VIX and crisis-period controls are added.", body_style))
story.append(Paragraph("H4 is not supported. After controlling for lagged VIX and major crisis periods, geopolitical risk is no longer a statistically significant predictor of VIX.", body_style))
story.append(Paragraph("H5 is partially supported. The enhanced forecasting model improves MAE and MAPE relative to the baseline model, but it has a slightly higher RMSE, indicating weaker performance during large volatility spikes.", body_style))

# ------------------------------------------------------------
# 10. Limitations
# ------------------------------------------------------------
story.append(Paragraph("10. Limitations", heading_style))

story.append(
    Paragraph(
        "One important limitation is multicollinearity. The correlation heatmap shows that several GPR variables are highly correlated, especially global GPR and U.S.-specific GPR. This means coefficient estimates in country-specific models should be interpreted cautiously.",
        body_style,
    )
)
story.append(
    Paragraph(
        "Another limitation is that the study uses monthly data, which may miss short-term market reactions to geopolitical events that occur within days. Financial markets may respond quickly to geopolitical events, while monthly averaging can smooth out those immediate effects.",
        body_style,
    )
)
story.append(
    Paragraph(
        "A further limitation is that the model does not include all possible macroeconomic or financial controls, such as unemployment, corporate credit spreads, exchange rates, equity returns, or global financial stress indexes. Future research could test whether geopolitical risk matters more in models using daily data or event-study methods.",
        body_style,
    )
)
story.append(
    Paragraph(
        "The forecasting backtest is also limited because it uses known historical values for explanatory variables during the test period. A true forward-looking forecast would require assumptions about future inflation, interest rates, oil prices, geopolitical risk, and crisis conditions.",
        body_style,
    )
)

# ------------------------------------------------------------
# 11. Conclusion
# ------------------------------------------------------------
story.append(Paragraph("11. Conclusion", heading_style))

story.append(
    Paragraph(
        "This study finds that geopolitical risk alone does not consistently explain U.S. market volatility from 2010 to 2025. The global GPR index is not statistically significant in the baseline models. U.S.-specific geopolitical risk appears significant in simpler country-specific and lagged models, but its significance disappears after controlling for lagged VIX and major crisis periods.",
        body_style,
    )
)
story.append(
    Paragraph(
        "The strongest predictors of VIX in the enhanced models are prior-month VIX, inflation, and the COVID-period dummy variable. These findings suggest that U.S. market volatility is driven more by volatility persistence, macroeconomic conditions, and major crisis shocks than by broad or country-specific geopolitical risk measures alone.",
        body_style,
    )
)
story.append(
    Paragraph(
        "The forecasting backtest shows that the enhanced model modestly improves average forecast accuracy, but sudden volatility spikes remain difficult to predict. This reinforces the broader conclusion that geopolitical risk and macroeconomic conditions can improve risk modeling, but volatility forecasting remains highly sensitive to unexpected shocks.",
        body_style,
    )
)
story.append(
    Paragraph(
        "The final conclusion is that the relationship between geopolitical risk and financial volatility is conditional rather than automatic. Geopolitical risk matters, but its measurable effect depends on timing, market expectations, the type of geopolitical event, and broader macroeconomic conditions.",
        body_style,
    )
)

# ------------------------------------------------------------
# 12. References and Data Sources
# ------------------------------------------------------------
story.append(Paragraph("12. References and Data Sources", heading_style))

references = [
    "Caldara, D., & Iacoviello, M. Geopolitical Risk Index data. Used for the global and country-specific GPR variables.",
    "Federal Reserve Economic Data (FRED). VIX, Brent crude oil, WTI crude oil, CPI, and Federal Funds Rate series.",
    "Office of the Director of National Intelligence. (2026). Annual Threat Assessment of the U.S. Intelligence Community. Used for current context on major-power competition, economic fragmentation, supply-chain and technology competition, and regional conflict risk. URL: https://www.dni.gov/files/ODNI/documents/assessments/ATA-2026-Unclassified-Report.pdf",
    "World Economic Forum. (2026). Global Risks Report 2026. Used for current context on geoeconomic confrontation, fragmentation, and global risk conditions. URL: https://reports.weforum.org/docs/WEF_Global_Risks_Report_2026.pdf",
    "International Monetary Fund. (2026). World Economic Outlook, April 2026: Global Economy in the Shadow of War. Used for current context on geopolitical-risk transmission channels, including energy markets, inflation, supply chains, uncertainty, and financial conditions. URL: https://www.imf.org/-/media/files/publications/weo/2026/april/english/text.pdf",
]

for ref in references:
    story.append(Paragraph(ref, small_style))

# ------------------------------------------------------------
# Save PDF
# ------------------------------------------------------------
doc.build(story, onFirstPage=page_number, onLaterPages=page_number)

print(f"PDF created successfully: {PDF_PATH}")
