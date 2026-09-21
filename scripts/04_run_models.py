from __future__ import annotations

from copy import copy
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "processed" / "final_model_dataset.xlsx"
RESULTS_DIR = REPO_ROOT / "results" / "tables"
FIGURES_DIR = REPO_ROOT / "results" / "figures"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

PURPLE = "#6B4EA0"
PURPLE_2 = "#A77BD6"
LIGHT_PURPLE = "#EFEAF8"
DARK = "#111111"
GREY = "#6B6B72"
LIGHT_GREY = "#E8E8EC"
GRID = "#E6E2EC"


def calc_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    err = y_true - y_pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot else float("nan")
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def style_ax(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#B9B5C4")
    ax.spines["bottom"].set_color("#B9B5C4")
    ax.tick_params(colors=DARK, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)


def add_reg_line(ax: plt.Axes, x: np.ndarray, y: np.ndarray, color: str) -> None:
    coef = np.polyfit(x, y, 1)
    xs = np.linspace(float(np.min(x)), float(np.max(x)), 100)
    ys = coef[0] * xs + coef[1]
    ax.plot(xs, ys, color=color, linewidth=2.2)


def prepare_supervised(df: pd.DataFrame) -> pd.DataFrame:
    supervised = df[
        [
            "YearMonth",
            "CPI_YoY_pct",
            "Avg_Temperature_F",
            "SW_EnergyDensity",
        ]
    ].copy()
    supervised = supervised.rename(
        columns={
            "YearMonth": "Target_YearMonth",
            "SW_EnergyDensity": "Target_EDP",
        }
    )
    return supervised[
        ["Target_YearMonth", "CPI_YoY_pct", "Avg_Temperature_F", "Target_EDP"]
    ].reset_index(drop=True)


def make_forecast_inputs(df: pd.DataFrame) -> pd.DataFrame:
    # Forecasting is treated as forward-looking for Jan-Mar 2024.
    # Therefore Jan-Mar 2024 external predictors are assumptions, not observed
    # 2024 data. CPI is held at the recent Q4 2023 average because short-horizon
    # inflation pressure is assumed to move gradually. Temperature is estimated
    # using the 2022-2023 same-calendar-month average because it is seasonal.
    q4_2023_cpi = float(
        df.loc[df["YearMonth"].isin(["2023-10", "2023-11", "2023-12"]), "CPI_YoY_pct"].mean()
    )
    jan_temp_assumption = float(
        df.loc[df["YearMonth"].isin(["2022-01", "2023-01"]), "Avg_Temperature_F"].mean()
    )
    feb_temp_assumption = float(
        df.loc[df["YearMonth"].isin(["2022-02", "2023-02"]), "Avg_Temperature_F"].mean()
    )
    mar_temp_assumption = float(
        df.loc[df["YearMonth"].isin(["2022-03", "2023-03"]), "Avg_Temperature_F"].mean()
    )

    return pd.DataFrame(
        [
            {
                "Forecast_Target_Month": "2024-01",
                "Predictor_Assumption_Month": "2024-01 assumption",
                "CPI_YoY_pct": q4_2023_cpi,
                "Avg_Temperature_F": jan_temp_assumption,
                "Assumption_Note": "CPI uses Q4 2023 average; temperature uses Jan 2022-2023 seasonal average.",
            },
            {
                "Forecast_Target_Month": "2024-02",
                "Predictor_Assumption_Month": "2024-02 assumption",
                "CPI_YoY_pct": q4_2023_cpi,
                "Avg_Temperature_F": feb_temp_assumption,
                "Assumption_Note": "CPI uses Q4 2023 average; temperature uses Feb 2022-2023 seasonal average.",
            },
            {
                "Forecast_Target_Month": "2024-03",
                "Predictor_Assumption_Month": "2024-03 assumption",
                "CPI_YoY_pct": q4_2023_cpi,
                "Avg_Temperature_F": mar_temp_assumption,
                "Assumption_Note": "CPI uses Q4 2023 average; temperature uses Mar 2022-2023 seasonal average.",
            },
        ]
    )


def main() -> None:
    df = pd.read_excel(DATA_PATH, sheet_name="02 Final Model Dataset")
    df["YearMonth"] = pd.PeriodIndex(df["YearMonth"], freq="M").astype(str)
    df = df.sort_values("YearMonth").reset_index(drop=True)
    supervised = prepare_supervised(df)

    features = ["CPI_YoY_pct", "Avg_Temperature_F"]
    n_train = 18
    train = supervised.iloc[:n_train].copy()
    test = supervised.iloc[n_train:].copy()

    x_train = train[features].to_numpy()
    y_train = train["Target_EDP"].to_numpy()
    x_test = test[features].to_numpy()
    y_test = test["Target_EDP"].to_numpy()

    baseline_pred = np.full(len(test), float(np.mean(y_train)))

    linear = LinearRegression().fit(x_train, y_train)
    linear_pred = linear.predict(x_test)

    rf = RandomForestRegressor(
        n_estimators=500,
        max_depth=3,
        min_samples_leaf=2,
        random_state=42,
    ).fit(x_train, y_train)
    rf_pred = rf.predict(x_test)

    metrics_df = pd.DataFrame(
        [
            {"Model": "Historical Mean Baseline", **calc_metrics(y_test, baseline_pred)},
            {"Model": "Linear Regression", **calc_metrics(y_test, linear_pred)},
            {"Model": "Random Forest", **calc_metrics(y_test, rf_pred)},
        ]
    )

    pred_df = test.copy()
    pred_df["Baseline_Prediction"] = baseline_pred
    pred_df["Linear_Regression_Prediction"] = linear_pred
    pred_df["Random_Forest_Prediction"] = rf_pred

    influence_df = pd.DataFrame(
        {
            "Feature": ["CPI YoY", "Monthly Average Temperature"],
            "Linear_Coefficient": linear.coef_,
            "RF_Feature_Importance": rf.feature_importances_,
        }
    )

    # Train on all 24 monthly observations for Jan-Mar 2024 forecasts.
    x_all = supervised[features].to_numpy()
    y_all = supervised["Target_EDP"].to_numpy()
    linear_final = LinearRegression().fit(x_all, y_all)
    rf_final = RandomForestRegressor(
        n_estimators=500,
        max_depth=3,
        min_samples_leaf=2,
        random_state=42,
    ).fit(x_all, y_all)

    forecast_inputs = make_forecast_inputs(df)
    forecast_x = forecast_inputs[features].to_numpy()
    forecast_df = forecast_inputs.copy()
    forecast_df["Historical_Mean_Forecast"] = float(np.mean(y_all))
    forecast_df["Linear_Regression_Forecast"] = linear_final.predict(forecast_x)
    forecast_df["Random_Forest_Forecast"] = rf_final.predict(forecast_x)

    # Forecast assumption map for Section 3 method explanation.
    assumption_map = forecast_df[
        [
            "Forecast_Target_Month",
            "Predictor_Assumption_Month",
            "CPI_YoY_pct",
            "Avg_Temperature_F",
        ]
    ].copy()
    assumption_map.columns = [
        "EDP forecast\nmonth",
        "External predictor\nassumption month",
        "CPI YoY\nassumption",
        "Temperature\nassumption",
    ]
    assumption_map["CPI YoY\nassumption"] = assumption_map["CPI YoY\nassumption"].map(
        lambda v: f"Q4 2023 avg = {v:.2f}%"
    )
    temp_notes = [
        "Jan 2022-2023 avg",
        "Feb 2022-2023 avg",
        "Mar 2022-2023 avg",
    ]
    assumption_map["Temperature\nassumption"] = [
        f"{note} = {temp:.2f}°F"
        for note, temp in zip(temp_notes, forecast_df["Avg_Temperature_F"])
    ]

    fig, ax = plt.subplots(figsize=(13.2, 3.5), dpi=260)
    ax.axis("off")
    ax.set_title("Forecast Input Assumptions for Jan-Mar 2024", fontsize=15.5, fontweight="bold", pad=18)
    table = ax.table(
        cellText=assumption_map.values,
        colLabels=assumption_map.columns,
        cellLoc="center",
        colLoc="center",
        loc="center",
        colWidths=[0.15, 0.23, 0.23, 0.31],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.55)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#D6D2DF")
        cell.set_linewidth(0.8)
        if row == 0:
            cell.set_facecolor(PURPLE)
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#FAF8FD" if row % 2 else "white")
    ax.text(
        0.5,
        0.03,
        "Future CPI and temperature values are treated as forecast assumptions, not observed 2024 data.",
        ha="center",
        va="center",
        fontsize=9,
        color=GREY,
        transform=ax.transAxes,
    )
    fig.savefig(FIGURES_DIR / "figure_3_forecast_assumption_map.png", bbox_inches="tight")
    plt.close(fig)

    # Exploratory Figure: target trend + relationships with each factor.
    fig = plt.figure(figsize=(10.8, 7.4), dpi=260)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1], hspace=0.36, wspace=0.28)
    ax1 = fig.add_subplot(gs[0, :])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    ax1.plot(
        df["YearMonth"],
        df["SW_EnergyDensity"],
        color=PURPLE,
        linewidth=2.7,
        marker="o",
        markersize=4.8,
        label="Monthly EDP Score",
    )
    ax1.axhline(df["SW_EnergyDensity"].mean(), color=GREY, linewidth=1.8, linestyle="--", label=f"Mean = {df['SW_EnergyDensity'].mean():.1f}")
    ax1.set_title("A. Monthly EDP Score trend (2022-2023)", fontsize=13, fontweight="bold", loc="left")
    ax1.set_ylabel("EDP Score")
    ax1.set_xticks(range(0, len(df), 3))
    ax1.set_xticklabels(df["YearMonth"].iloc[::3], rotation=0)
    ax1.legend(frameon=False, fontsize=9, loc="upper right")
    style_ax(ax1)

    cpi_x = supervised["CPI_YoY_pct"].to_numpy()
    target_y = supervised["Target_EDP"].to_numpy()
    corr_cpi = float(np.corrcoef(cpi_x, target_y)[0, 1])
    ax2.scatter(cpi_x, target_y, s=52, color=PURPLE, alpha=0.86, edgecolor="white", linewidth=0.8)
    add_reg_line(ax2, cpi_x, target_y, PURPLE)
    ax2.set_title(f"B. CPI YoY vs monthly EDP (r = {corr_cpi:.2f})", fontsize=12, fontweight="bold", loc="left")
    ax2.set_xlabel("Monthly CPI YoY (%)")
    ax2.set_ylabel("Monthly EDP Score")
    style_ax(ax2)

    temp_x = supervised["Avg_Temperature_F"].to_numpy()
    corr_temp = float(np.corrcoef(temp_x, target_y)[0, 1])
    ax3.scatter(temp_x, target_y, s=52, color=PURPLE_2, alpha=0.86, edgecolor="white", linewidth=0.8)
    add_reg_line(ax3, temp_x, target_y, PURPLE_2)
    ax3.set_title(f"C. Temperature vs monthly EDP (r = {corr_temp:.2f})", fontsize=12, fontweight="bold", loc="left")
    ax3.set_xlabel("Monthly average temperature (°F)")
    ax3.set_ylabel("Monthly EDP Score")
    style_ax(ax3)
    fig.suptitle("Exploratory Results: EDP Trend and Factor Relationships", fontsize=16, fontweight="bold", y=0.985)
    fig.text(0.5, 0.01, "Relationships use monthly external factors and same-month EDP Score.", ha="center", color=GREY, fontsize=9)
    fig.savefig(FIGURES_DIR / "figure_2_exploratory_edp_relationships.png", bbox_inches="tight")
    plt.close(fig)

    # Model performance Figure: actual vs predicted + error comparison.
    fig = plt.figure(figsize=(10.8, 6.4), dpi=260)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1], wspace=0.3)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    x = np.arange(len(pred_df))
    ax1.plot(x, pred_df["Target_EDP"], color=DARK, linewidth=2.8, marker="o", label="Actual EDP")
    ax1.plot(x, pred_df["Baseline_Prediction"], color="#9A9A9A", linewidth=2.1, linestyle="--", marker="o", label="Baseline")
    ax1.plot(x, pred_df["Linear_Regression_Prediction"], color=PURPLE, linewidth=2.3, marker="o", label="Linear Regression")
    ax1.plot(x, pred_df["Random_Forest_Prediction"], color=PURPLE_2, linewidth=2.3, marker="o", label="Random Forest")
    ax1.set_title("A. Test-period actual vs predicted EDP", fontsize=12.5, fontweight="bold", loc="left")
    ax1.set_xticks(x)
    ax1.set_xticklabels(pred_df["Target_YearMonth"])
    ax1.set_xlabel("Target month")
    ax1.set_ylabel("EDP Score")
    ax1.text(0.02, 0.04, "Chronological test period", transform=ax1.transAxes, fontsize=9, color=GREY)
    ax1.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper right")
    style_ax(ax1)

    bar_x = np.arange(len(metrics_df))
    width = 0.34
    ax2.bar(bar_x - width / 2, metrics_df["MAE"], width, color=PURPLE, label="MAE")
    ax2.bar(bar_x + width / 2, metrics_df["RMSE"], width, color=PURPLE_2, label="RMSE")
    for i, row in metrics_df.iterrows():
        ax2.text(i - width / 2, row["MAE"] + 0.12, f"{row['MAE']:.2f}", ha="center", fontsize=8.5)
        ax2.text(i + width / 2, row["RMSE"] + 0.12, f"{row['RMSE']:.2f}", ha="center", fontsize=8.5)
    ax2.set_title("B. Test-period prediction error", fontsize=12.5, fontweight="bold", loc="left")
    ax2.set_xticks(bar_x)
    ax2.set_xticklabels(["Baseline", "Linear\nRegression", "Random\nForest"])
    ax2.set_ylabel("Error in EDP Score")
    ax2.legend(frameon=False, fontsize=9)
    style_ax(ax2)
    fig.suptitle("Model Performance Results", fontsize=16, fontweight="bold", y=0.99)
    fig.savefig(FIGURES_DIR / "figure_3_model_performance_refined.png", bbox_inches="tight")
    plt.close(fig)

    # Factor influence Figure: regression direction + tree feature importance.
    fig = plt.figure(figsize=(10.8, 5.8), dpi=260)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1], wspace=0.28)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    coef_colors = [PURPLE if v >= 0 else "#B15A5A" for v in influence_df["Linear_Coefficient"]]
    coef_labels = ["CPI YoY", "Monthly\nTemperature"]
    ax1.bar(coef_labels, influence_df["Linear_Coefficient"], color=coef_colors, alpha=0.95, width=0.52)
    ax1.axhline(0, color=GREY, linewidth=1.2)
    for i, v in enumerate(influence_df["Linear_Coefficient"]):
        if v >= 0:
            ax1.text(i, v - 0.055, f"{v:.3f}", va="top", ha="center", fontsize=10, color="white", fontweight="bold")
        else:
            ax1.text(i, 0.035, f"{v:.3f}", va="bottom", ha="center", fontsize=10, color="#7B3F3F", fontweight="bold")
    ax1.set_ylim(-0.16, 1.02)
    ax1.set_title("A. Linear Regression coefficients", fontsize=12.5, fontweight="bold", loc="left")
    ax1.set_ylabel("Coefficient")
    style_ax(ax1)

    importance_labels = ["CPI YoY", "Monthly\nTemperature"]
    ax2.bar(importance_labels, influence_df["RF_Feature_Importance"], color=[PURPLE, PURPLE_2], width=0.52)
    for i, v in enumerate(influence_df["RF_Feature_Importance"]):
        ax2.text(i, v + 0.025, f"{v:.1%}", ha="center", fontsize=10)
    ax2.set_ylim(0, 1)
    ax2.set_title("B. Random Forest feature importance", fontsize=12.5, fontweight="bold", loc="left")
    ax2.set_ylabel("Share of feature importance")
    style_ax(ax2)
    fig.suptitle("Factor Influence: Direction and Relative Importance", fontsize=16, fontweight="bold", y=0.99)
    fig.savefig(FIGURES_DIR / "figure_4_factor_influence_refined.png", bbox_inches="tight")
    plt.close(fig)

    # Forecast table figure. A table is clearer than a flat line chart because
    # Jan-Mar assumptions are intentionally conservative and close together.
    forecast_display = forecast_df[
        [
            "Forecast_Target_Month",
            "CPI_YoY_pct",
            "Avg_Temperature_F",
            "Linear_Regression_Forecast",
            "Random_Forest_Forecast",
        ]
    ].copy()
    forecast_display.columns = [
        "Target\nMonth",
        "CPI YoY\nAssumption (%)",
        "Temperature\nAssumption (°F)",
        "Linear Regression\nForecast",
        "Random Forest\nForecast",
    ]
    for col in forecast_display.columns[1:]:
        forecast_display[col] = forecast_display[col].map(lambda v: f"{v:.2f}")

    fig, ax = plt.subplots(figsize=(10.8, 4.4), dpi=260)
    ax.axis("off")
    ax.set_title("Jan-Mar 2024 EDP Forecast Under Forward-Looking Assumptions", fontsize=15, fontweight="bold", pad=18)
    table = ax.table(
        cellText=forecast_display.values,
        colLabels=forecast_display.columns,
        cellLoc="center",
        colLoc="center",
        loc="center",
        colWidths=[0.16, 0.22, 0.22, 0.20, 0.20],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.05)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#B7D9EA")
        cell.set_linewidth(0.8)
        if row == 0:
            cell.set_facecolor("#D9EEF7")
            cell.get_text().set_color(DARK)
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#F2FAFD" if row % 2 else "white")
    ax.text(
        0.5,
        0.02,
        "CPI uses Q4 2023 average; temperature uses same-calendar-month 2022-2023 seasonal averages. Actual 2024 sales/external data are not used.",
        ha="center",
        va="center",
        fontsize=9,
        color=GREY,
        transform=ax.transAxes,
    )
    fig.savefig(FIGURES_DIR / "figure_5_jan_mar_2024_forecast_table.png", bbox_inches="tight")
    plt.close(fig)

    # Save outputs.
    supervised.to_csv(RESULTS_DIR / "model_dataset.csv", index=False)
    pred_df.to_csv(RESULTS_DIR / "test_predictions.csv", index=False)
    metrics_df.to_csv(RESULTS_DIR / "model_metrics.csv", index=False)
    influence_df.to_csv(RESULTS_DIR / "factor_influence.csv", index=False)
    forecast_df.to_csv(RESULTS_DIR / "forecast_jan_mar_2024.csv", index=False)

    with pd.ExcelWriter(RESULTS_DIR / "model_results.xlsx", engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {"Item": "Supervised observations", "Value": len(supervised)},
                {"Item": "Training observations", "Value": len(train)},
                {"Item": "Test observations", "Value": len(test)},
                {"Item": "Training target months", "Value": f"{train['Target_YearMonth'].min()} to {train['Target_YearMonth'].max()}"},
                {"Item": "Test target months", "Value": f"{test['Target_YearMonth'].min()} to {test['Target_YearMonth'].max()}"},
                {"Item": "Forecast assumption rule", "Value": "2024 predictor inputs estimated from 2022-2023 historical patterns; actual 2024 sales are not used."},
            ]
        ).to_excel(writer, sheet_name="00 Summary", index=False)
        supervised.to_excel(writer, sheet_name="01 Model Dataset", index=False)
        metrics_df.to_excel(writer, sheet_name="02 Model Metrics", index=False)
        pred_df.to_excel(writer, sheet_name="03 Test Predictions", index=False)
        influence_df.to_excel(writer, sheet_name="04 Factor Influence", index=False)
        forecast_df.to_excel(writer, sheet_name="05 Jan-Mar Forecast", index=False)
        for ws in writer.book.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    alignment = copy(cell.alignment)
                    alignment.wrap_text = True
                    alignment.vertical = "top"
                    cell.alignment = alignment
            for col in ws.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 3, 12), 55)

    print("METRICS")
    print(metrics_df.round(4).to_string(index=False))
    print("\nINFLUENCE")
    print(influence_df.round(4).to_string(index=False))
    print("\nFORECAST")
    print(forecast_df.round(4).to_string(index=False))
    print("\nFIGURES")
    for path in [
        FIGURES_DIR / "figure_2_exploratory_edp_relationships.png",
        FIGURES_DIR / "figure_3_model_performance_refined.png",
        FIGURES_DIR / "figure_4_factor_influence_refined.png",
        FIGURES_DIR / "figure_5_jan_mar_2024_forecast_table.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
