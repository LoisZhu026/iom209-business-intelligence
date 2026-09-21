from __future__ import annotations

from copy import copy
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MONTHLY_DV_PATH = (
    REPO_ROOT / "data" / "derived" / "energy_mapping" / "monthly_sw_energy_density.csv"
)
EXTERNAL_FACTORS_PATH = (
    REPO_ROOT / "data" / "derived" / "external_factors" / "external_factors_model_table.csv"
)


def main() -> None:
    dv = pd.read_csv(MONTHLY_DV_PATH)
    factors = pd.read_csv(EXTERNAL_FACTORS_PATH)

    required_dv = {
        "YearMonth",
        "Total_Food_Portions",
        "Mapped_Food_Portions",
        "Coverage_Rate",
        "SW_EnergyDensity",
        "Mapped_Rows",
    }
    required_factors = {
        "YearMonth",
        "CPIAUCSL",
        "CPI_YoY_pct",
        "CPI_MoM_pct",
        "Avg_Temperature_F",
        "Avg_Temperature_C",
    }
    missing_dv = required_dv - set(dv.columns)
    missing_factors = required_factors - set(factors.columns)
    if missing_dv:
        raise ValueError(f"Monthly DV missing columns: {missing_dv}")
    if missing_factors:
        raise ValueError(f"External factors missing columns: {missing_factors}")

    model = dv.merge(factors, on="YearMonth", how="inner")
    expected_months = pd.period_range("2022-01", "2023-12", freq="M").astype(str).tolist()
    missing_months = sorted(set(expected_months) - set(model["YearMonth"]))
    extra_months = sorted(set(model["YearMonth"]) - set(expected_months))
    if missing_months or extra_months:
        raise ValueError(
            f"Unexpected model months. missing={missing_months}, extra={extra_months}"
        )
    if model["YearMonth"].duplicated().any():
        raise ValueError("Duplicated YearMonth values in model dataset")
    if model.isna().any().any():
        raise ValueError(f"Model dataset contains NA values:\n{model.isna().sum()}")

    model = model[
        [
            "YearMonth",
            "SW_EnergyDensity",
            "CPI_YoY_pct",
            "Avg_Temperature_F",
            "CPIAUCSL",
            "CPI_MoM_pct",
            "Avg_Temperature_C",
            "Total_Food_Portions",
            "Mapped_Food_Portions",
            "Coverage_Rate",
            "Mapped_Rows",
        ]
    ]

    metadata = pd.DataFrame(
        [
            {
                "Variable": "YearMonth",
                "Meaning": "Monthly time period from 2022-01 to 2023-12.",
                "Use": "Time index.",
            },
            {
                "Variable": "SW_EnergyDensity",
                "Meaning": "Energy-Density Preference Score (EDP Score): monthly quantity-weighted average of USDA-mapped kcal per 100g for included sold food portions.",
                "Use": "Dependent variable.",
            },
            {
                "Variable": "CPI_YoY_pct",
                "Meaning": "Year-on-year percentage change in FRED CPIAUCSL.",
                "Use": "Economic factor / predictor.",
            },
            {
                "Variable": "Avg_Temperature_F",
                "Meaning": "Monthly average Austin daily TAVG in Fahrenheit.",
                "Use": "Weather factor / predictor.",
            },
            {
                "Variable": "CPIAUCSL",
                "Meaning": "Monthly CPI index level retained for audit/reference.",
                "Use": "Reference only; not preferred as the main CPI theoretical variable.",
            },
            {
                "Variable": "CPI_MoM_pct",
                "Meaning": "Month-on-month CPI percentage change retained for audit/reference.",
                "Use": "Reference only.",
            },
            {
                "Variable": "Avg_Temperature_C",
                "Meaning": "Monthly average Austin daily TAVG in Celsius.",
                "Use": "Reference only; Fahrenheit is used because the source data is in Fahrenheit.",
            },
            {
                "Variable": "Coverage_Rate",
                "Meaning": "Mapped_Food_Portions / Total_Food_Portions.",
                "Use": "Data quality check for DV construction.",
            },
        ]
    )

    summary = pd.DataFrame(
        [
            {"Metric": "Model months", "Value": len(model)},
            {"Metric": "Date range", "Value": f"{model['YearMonth'].min()} to {model['YearMonth'].max()}"},
            {"Metric": "Missing values", "Value": int(model.isna().sum().sum())},
            {"Metric": "Duplicate months", "Value": int(model["YearMonth"].duplicated().sum())},
            {"Metric": "Mean EDP Score", "Value": round(model["SW_EnergyDensity"].mean(), 4)},
            {"Metric": "Min EDP Score", "Value": round(model["SW_EnergyDensity"].min(), 4)},
            {"Metric": "Max EDP Score", "Value": round(model["SW_EnergyDensity"].max(), 4)},
            {"Metric": "Mean coverage rate", "Value": round(model["Coverage_Rate"].mean(), 4)},
            {"Metric": "Main predictors", "Value": "CPI_YoY_pct; Avg_Temperature_F"},
        ]
    )

    csv_path = OUTPUT_DIR / "final_model_dataset.csv"
    xlsx_path = OUTPUT_DIR / "final_model_dataset.xlsx"

    model.to_csv(csv_path, index=False)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="00 Read Me")
        metadata.to_excel(writer, index=False, sheet_name="01 Metadata")
        model.to_excel(writer, index=False, sheet_name="02 Final Model Dataset")
        for ws in writer.book.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    alignment = copy(cell.alignment)
                    alignment.wrap_text = True
                    alignment.vertical = "top"
                    cell.alignment = alignment
            for col in ws.columns:
                col_letter = col[0].column_letter
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 55)

    print(csv_path)
    print(xlsx_path)


if __name__ == "__main__":
    main()
