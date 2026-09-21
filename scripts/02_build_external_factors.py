from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "derived" / "external_factors"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CPI_2021_PATH = REPO_ROOT / "data" / "external" / "cpi_2021.csv"
CPI_2022_2023_PATH = (
    REPO_ROOT / "data" / "external" / "economic_cpi_2022_2023.csv"
)
WEATHER_PATH = (
    REPO_ROOT / "data" / "external" / "weather_austin_daily_2022_2023.csv"
)


def pct_change_yoy(series: pd.Series) -> pd.Series:
    return series.pct_change(12) * 100


def clean_records(df: pd.DataFrame) -> list[dict]:
    cleaned = df.astype(object).where(pd.notna(df), None)
    return cleaned.to_dict(orient="records")


def main() -> None:
    cpi_2021 = pd.read_csv(CPI_2021_PATH)
    cpi_existing = pd.read_csv(CPI_2022_2023_PATH)
    cpi_raw = (
        pd.concat([cpi_2021, cpi_existing], ignore_index=True)
        .drop_duplicates(subset=["observation_date"])
        .sort_values("observation_date")
        .reset_index(drop=True)
    )
    cpi_raw["observation_date"] = pd.to_datetime(cpi_raw["observation_date"])
    cpi_raw["YearMonth"] = cpi_raw["observation_date"].dt.strftime("%Y-%m")
    cpi_raw["CPIAUCSL"] = pd.to_numeric(cpi_raw["CPIAUCSL"], errors="coerce")
    cpi_raw["CPI_YoY_pct"] = pct_change_yoy(cpi_raw["CPIAUCSL"])
    cpi_raw["CPI_MoM_pct"] = cpi_raw["CPIAUCSL"].pct_change(1) * 100

    expected = pd.date_range("2021-01-01", "2023-12-01", freq="MS")
    missing_months = expected.difference(cpi_raw["observation_date"])
    if len(missing_months) > 0:
        raise ValueError(f"CPI data has missing months: {list(missing_months)}")

    cpi_model = cpi_raw[
        (cpi_raw["observation_date"] >= "2022-01-01")
        & (cpi_raw["observation_date"] <= "2023-12-01")
    ].copy()
    cpi_model = cpi_model[
        ["YearMonth", "observation_date", "CPIAUCSL", "CPI_YoY_pct", "CPI_MoM_pct"]
    ]

    weather_daily = pd.read_csv(WEATHER_PATH)
    weather_daily["DATE"] = pd.to_datetime(weather_daily["DATE"], dayfirst=True)
    for col in ["AWND", "PRCP", "TAVG"]:
        weather_daily[col] = pd.to_numeric(weather_daily[col], errors="coerce")
    weather_daily["YearMonth"] = weather_daily["DATE"].dt.strftime("%Y-%m")

    weather_monthly = (
        weather_daily.groupby("YearMonth", as_index=False)
        .agg(
            Days_Observed=("DATE", "count"),
            Avg_Temperature_F=("TAVG", "mean"),
            Avg_Wind_Speed=("AWND", "mean"),
            Total_Precipitation=("PRCP", "sum"),
        )
        .sort_values("YearMonth")
    )
    weather_monthly["Avg_Temperature_C"] = (
        (weather_monthly["Avg_Temperature_F"] - 32) * 5 / 9
    )
    weather_monthly = weather_monthly[
        [
            "YearMonth",
            "Days_Observed",
            "Avg_Temperature_F",
            "Avg_Temperature_C",
            "Avg_Wind_Speed",
            "Total_Precipitation",
        ]
    ]

    expected_model_months = pd.period_range("2022-01", "2023-12", freq="M").astype(str)
    missing_weather = set(expected_model_months) - set(weather_monthly["YearMonth"])
    if missing_weather:
        raise ValueError(f"Weather data has missing months: {sorted(missing_weather)}")

    external_factors = cpi_model.merge(
        weather_monthly[["YearMonth", "Avg_Temperature_F", "Avg_Temperature_C"]],
        on="YearMonth",
        how="left",
    )
    external_factors = external_factors[
        [
            "YearMonth",
            "CPIAUCSL",
            "CPI_YoY_pct",
            "CPI_MoM_pct",
            "Avg_Temperature_F",
            "Avg_Temperature_C",
        ]
    ]

    metadata = [
        {
            "Sheet_or_Variable": "CPIAUCSL",
            "Meaning": "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average, seasonally adjusted monthly index.",
            "Source_or_Method": "FRED series CPIAUCSL. 2021 values are retained only to calculate 2022 year-on-year CPI change; model period remains 2022-2023.",
        },
        {
            "Sheet_or_Variable": "CPI_YoY_pct",
            "Meaning": "Year-on-year percentage change in CPIAUCSL, used as the report's inflation pressure variable.",
            "Source_or_Method": "(CPI_t - CPI_t-12) / CPI_t-12 * 100.",
        },
        {
            "Sheet_or_Variable": "CPI_MoM_pct",
            "Meaning": "Month-on-month percentage change in CPIAUCSL, retained for audit/reference but not preferred as the main theoretical factor.",
            "Source_or_Method": "(CPI_t - CPI_t-1) / CPI_t-1 * 100.",
        },
        {
            "Sheet_or_Variable": "Avg_Temperature_F",
            "Meaning": "Monthly average of daily Austin TAVG, used as the weather factor.",
            "Source_or_Method": "Group coursework weather file aggregated from daily rows to monthly frequency.",
        },
        {
            "Sheet_or_Variable": "External Factors Model Table",
            "Meaning": "Final monthly external factor table for merging with the monthly dependent variable.",
            "Source_or_Method": "Uses 2022-2023 months only to match The Bistro sales timeline.",
        },
    ]

    summary = {
        "CPI raw date range": f"{cpi_raw['YearMonth'].min()} to {cpi_raw['YearMonth'].max()}",
        "CPI raw months": len(cpi_raw),
        "CPI missing months": len(missing_months),
        "Weather raw daily rows": len(weather_daily),
        "Weather monthly rows": len(weather_monthly),
        "External factor model months": len(external_factors),
        "Main CPI variable": "CPI_YoY_pct",
        "Main weather variable": "Avg_Temperature_F",
    }

    cpi_raw_out = cpi_raw.copy()
    cpi_raw_out["observation_date"] = cpi_raw_out["observation_date"].dt.strftime(
        "%Y-%m-%d"
    )
    cpi_model_out = cpi_model.copy()
    cpi_model_out["observation_date"] = cpi_model_out["observation_date"].dt.strftime(
        "%Y-%m-%d"
    )
    weather_daily_out = weather_daily.copy()
    weather_daily_out["DATE"] = weather_daily_out["DATE"].dt.strftime("%Y-%m-%d")

    outputs = {
        "summary": summary,
        "metadata": metadata,
        "cpi_raw_2021_2023": clean_records(cpi_raw_out),
        "cpi_model_variable_2022_2023": clean_records(cpi_model_out),
        "weather_daily_raw_2022_2023": weather_daily_out[
            ["DATE", "YearMonth", "AWND", "PRCP", "TAVG"]
        ].pipe(clean_records),
        "weather_monthly_2022_2023": clean_records(weather_monthly),
        "external_factors_model_table": clean_records(external_factors),
    }

    json_path = OUTPUT_DIR / "external_factors_outputs.json"
    json_path.write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding="utf-8")

    cpi_raw_out.to_csv(OUTPUT_DIR / "cpi_raw_2021_2023.csv", index=False)
    cpi_model_out.to_csv(OUTPUT_DIR / "cpi_model_variable_2022_2023.csv", index=False)
    weather_daily_out.to_csv(OUTPUT_DIR / "weather_daily_raw_2022_2023.csv", index=False)
    weather_monthly.to_csv(OUTPUT_DIR / "weather_monthly_2022_2023.csv", index=False)
    external_factors.to_csv(OUTPUT_DIR / "external_factors_model_table.csv", index=False)

    print(json_path)


if __name__ == "__main__":
    main()
