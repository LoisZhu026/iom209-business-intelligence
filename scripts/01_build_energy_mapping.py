import json
import math
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SALES_PATH = REPO_ROOT / "data" / "raw" / "the_bistro_data_final.xlsx"
OUTPUT_DIR = REPO_ROOT / "data" / "derived" / "energy_mapping"


MAPPING_ROWS = [
    {
        "Bistro_Item": "Grilled Chicken",
        "Category": "Main Dishes",
        "USDA_Comparable_Food": "Chicken breast, grilled without sauce, skin not eaten",
        "FDC_ID": 2705968,
        "Energy_kcal_per_100g": 176,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Uses grilled chicken breast without sauce as closest comparable food.",
    },
    {
        "Bistro_Item": "Pasta Alfredo",
        "Category": "Main Dishes",
        "USDA_Comparable_Food": "Pasta with cream sauce, restaurant",
        "FDC_ID": 2708855,
        "Energy_kcal_per_100g": 204,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Restaurant pasta with cream sauce used as comparable to Alfredo-style pasta.",
    },
    {
        "Bistro_Item": "Salmon",
        "Category": "Main Dishes",
        "USDA_Comparable_Food": "Fish, salmon, grilled",
        "FDC_ID": 2706287,
        "Energy_kcal_per_100g": 259,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Uses grilled salmon as closest preparation match.",
    },
    {
        "Bistro_Item": "Steak",
        "Category": "Main Dishes",
        "USDA_Comparable_Food": "Beef, steak, NFS",
        "FDC_ID": 2705824,
        "Energy_kcal_per_100g": 229,
        "Match_Quality": "Transparent approximate comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Steak cut is not specified in Bistro data; USDA generic steak is used.",
    },
    {
        "Bistro_Item": "Vegetarian Platter",
        "Category": "Main Dishes",
        "USDA_Comparable_Food": "No defensible direct equivalent",
        "FDC_ID": None,
        "Energy_kcal_per_100g": None,
        "Match_Quality": "Insufficient detail",
        "Inclusion_Decision": "Exclude from main analysis",
        "Assumption_or_Treatment": "Composition is unspecified; assigning a USDA proxy would require guessing ingredients.",
    },
    {
        "Bistro_Item": "Beef Chili",
        "Category": "Starters",
        "USDA_Comparable_Food": "Chili with meat, from restaurant",
        "FDC_ID": 2706374,
        "Energy_kcal_per_100g": 160,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Restaurant chili with meat used as comparable.",
    },
    {
        "Bistro_Item": "Cheese Fries",
        "Category": "Starters",
        "USDA_Comparable_Food": "Potato, french fries, with cheese, fast food / restaurant",
        "FDC_ID": 2709465,
        "Energy_kcal_per_100g": 260,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Restaurant/fast-food cheese fries used as comparable.",
    },
    {
        "Bistro_Item": "Chicken Melt",
        "Category": "Starters",
        "USDA_Comparable_Food": "Chicken deli sandwich or sub, with cheese, restaurant",
        "FDC_ID": 2706989,
        "Energy_kcal_per_100g": 208,
        "Match_Quality": "Transparent approximate comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Bistro data does not define 'melt'; interpreted as chicken-and-cheese sandwich-style item.",
    },
    {
        "Bistro_Item": "French Fries",
        "Category": "Starters",
        "USDA_Comparable_Food": "Potato, french fries, restaurant",
        "FDC_ID": 2709462,
        "Energy_kcal_per_100g": 289,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Restaurant french fries used as comparable.",
    },
    {
        "Bistro_Item": "Nachos Grande",
        "Category": "Starters",
        "USDA_Comparable_Food": "Nachos, NFS",
        "FDC_ID": 2708576,
        "Energy_kcal_per_100g": 265,
        "Match_Quality": "Transparent approximate comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Toppings are unspecified; USDA generic nachos are used.",
    },
    {
        "Bistro_Item": "Sweet Potato Fries",
        "Category": "Starters",
        "USDA_Comparable_Food": "Sweet potato fries, fast food / restaurant",
        "FDC_ID": 2709713,
        "Energy_kcal_per_100g": 305,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Restaurant/fast-food sweet potato fries used as comparable.",
    },
    {
        "Bistro_Item": "Garlic Bread",
        "Category": "Side Dishes",
        "USDA_Comparable_Food": "Garlic bread, from fast food / restaurant",
        "FDC_ID": 2707627,
        "Energy_kcal_per_100g": 349,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Restaurant/fast-food garlic bread used as comparable.",
    },
    {
        "Bistro_Item": "Grilled Vegetables",
        "Category": "Side Dishes",
        "USDA_Comparable_Food": "Classic mixed vegetables, cooked, from restaurant",
        "FDC_ID": 2710012,
        "Energy_kcal_per_100g": 100,
        "Match_Quality": "Transparent approximate comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "USDA lacks a direct grilled-vegetables entry; restaurant cooked mixed vegetables are used as conservative proxy.",
    },
    {
        "Bistro_Item": "Mashed Potatoes",
        "Category": "Side Dishes",
        "USDA_Comparable_Food": "Potato, mashed, from restaurant",
        "FDC_ID": 2709500,
        "Energy_kcal_per_100g": 138,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Restaurant mashed potatoes used as comparable.",
    },
    {
        "Bistro_Item": "Onion Rings",
        "Category": "Side Dishes",
        "USDA_Comparable_Food": "Fried onion rings",
        "FDC_ID": 2710055,
        "Energy_kcal_per_100g": 352,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Fried onion rings used as comparable.",
    },
    {
        "Bistro_Item": "Side Salad",
        "Category": "Side Dishes",
        "USDA_Comparable_Food": "Lettuce, salad with assorted vegetables including tomatoes and/or carrots, no dressing",
        "FDC_ID": 2709822,
        "Energy_kcal_per_100g": 24,
        "Match_Quality": "Transparent approximate comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Dressing is not specified in Bistro item name; no-dressing salad is used.",
    },
    {
        "Bistro_Item": "Brownie",
        "Category": "Desserts",
        "USDA_Comparable_Food": "Cookie, brownie, without icing",
        "FDC_ID": 2707904,
        "Energy_kcal_per_100g": 405,
        "Match_Quality": "Transparent approximate comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Bistro item does not specify icing; no-icing brownie is used.",
    },
    {
        "Bistro_Item": "Cheesecake",
        "Category": "Desserts",
        "USDA_Comparable_Food": "Cheesecake, plain",
        "FDC_ID": 2707861,
        "Energy_kcal_per_100g": 399,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Plain cheesecake used as comparable.",
    },
    {
        "Bistro_Item": "Chocolate Cake",
        "Category": "Desserts",
        "USDA_Comparable_Food": "Cake or cupcake, chocolate with chocolate icing, bakery",
        "FDC_ID": 2707866,
        "Energy_kcal_per_100g": 345,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Bakery chocolate cake with chocolate icing used as comparable.",
    },
    {
        "Bistro_Item": "Fruit Salad",
        "Category": "Desserts",
        "USDA_Comparable_Food": "Fruit salad, fresh or raw, excluding citrus fruits, no dressing",
        "FDC_ID": 2709287,
        "Energy_kcal_per_100g": 59,
        "Match_Quality": "Direct comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Fresh fruit salad without dressing used as comparable.",
    },
    {
        "Bistro_Item": "Ice Cream",
        "Category": "Desserts",
        "USDA_Comparable_Food": "Ice cream, vanilla",
        "FDC_ID": 2705630,
        "Energy_kcal_per_100g": 207,
        "Match_Quality": "Transparent approximate comparable",
        "Inclusion_Decision": "Include",
        "Assumption_or_Treatment": "Bistro flavor unspecified; vanilla ice cream used as standard comparable.",
    },
]


def clean_for_json(value):
    if isinstance(value, dict):
        return {k: clean_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_for_json(v) for v in value]
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


STATUS_REASON = {
    "Mapped known item": "Original item is known and has a defensible USDA comparable food.",
    "Recovered exact item via Category+Price": "Original item was Unknown, but Category+Price uniquely identifies one included Bistro item.",
    "Excluded: Vegetarian Platter composition unspecified": "Dish composition is unspecified; assigning a USDA comparable food would require guessing ingredients.",
    "Excluded: ambiguous unknown item": "Original item is Unknown and Category+Price does not uniquely identify one included mapped item.",
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sales = pd.read_excel(SALES_PATH)
    sales["YearMonth"] = pd.to_datetime(sales["Order Date"]).dt.to_period("M").astype(str)

    mapping = pd.DataFrame(MAPPING_ROWS)
    prices = (
        sales[(sales["Item"] != "Unknown") & (sales["Category"] != "Drinks")]
        .groupby("Item", as_index=False)["Price"]
        .first()
        .rename(columns={"Item": "Bistro_Item", "Price": "Bistro_Price"})
    )
    mapping = mapping.merge(prices, on="Bistro_Item", how="left")
    mapping.insert(2, "Bistro_Price", mapping.pop("Bistro_Price"))
    mapping["USDA_Source"] = "USDA FoodData Central, FNDDS 2021-2023"

    included_mapping = mapping[mapping["Inclusion_Decision"] == "Include"].copy()
    energy_by_item = included_mapping.set_index("Bistro_Item")["Energy_kcal_per_100g"].to_dict()
    quality_by_item = included_mapping.set_index("Bistro_Item")["Match_Quality"].to_dict()

    food_sales = sales[sales["Category"] != "Drinks"].copy()
    food_sales["Mapped_Item"] = food_sales["Item"]
    food_sales["Energy_kcal_per_100g"] = food_sales["Item"].map(energy_by_item)
    food_sales["Mapping_Status"] = "Mapped known item"
    food_sales.loc[food_sales["Category"] == "Drinks", "Mapping_Status"] = "Excluded: drink"

    food_sales.loc[
        food_sales["Item"] == "Vegetarian Platter", "Mapping_Status"
    ] = "Excluded: Vegetarian Platter composition unspecified"

    known_included = food_sales[
        (food_sales["Item"] != "Unknown") & (food_sales["Item"].isin(energy_by_item))
    ].copy()

    # Recover unknown rows only when Category + Price points to a single included Bistro item.
    candidate_groups = (
        known_included.groupby(["Category", "Price"])["Item"]
        .agg(lambda x: sorted(set(x)))
        .reset_index()
    )
    exact_lookup = {
        (row["Category"], row["Price"]): row["Item"][0]
        for _, row in candidate_groups.iterrows()
        if len(row["Item"]) == 1
    }
    all_lookup = {
        (row["Category"], row["Price"]): row["Item"]
        for _, row in candidate_groups.iterrows()
    }

    for idx, row in food_sales[food_sales["Item"] == "Unknown"].iterrows():
        key = (row["Category"], row["Price"])
        if key in exact_lookup:
            recovered_item = exact_lookup[key]
            food_sales.at[idx, "Mapped_Item"] = recovered_item
            food_sales.at[idx, "Energy_kcal_per_100g"] = energy_by_item[recovered_item]
            food_sales.at[idx, "Mapping_Status"] = "Recovered exact item via Category+Price"
        else:
            candidates = all_lookup.get(key, [])
            food_sales.at[idx, "Mapped_Item"] = (
                "; ".join(candidates) if candidates else "No included candidate"
            )
            food_sales.at[idx, "Mapping_Status"] = "Excluded: ambiguous unknown item"

    food_sales["Weighted_EnergyDensity"] = (
        food_sales["Energy_kcal_per_100g"] * food_sales["Quantity"]
    )

    monthly_total = (
        food_sales.groupby("YearMonth")["Quantity"]
        .sum()
        .rename("Total_Food_Portions")
        .reset_index()
    )
    mapped_sales = food_sales[food_sales["Energy_kcal_per_100g"].notna()].copy()
    monthly_mapped = (
        mapped_sales.groupby("YearMonth")
        .agg(
            Mapped_Food_Portions=("Quantity", "sum"),
            Weighted_EnergyDensity_Sum=("Weighted_EnergyDensity", "sum"),
            Mapped_Rows=("Order ID", "size"),
        )
        .reset_index()
    )
    monthly = monthly_total.merge(monthly_mapped, on="YearMonth", how="left").fillna(0)
    monthly["Coverage_Rate"] = monthly["Mapped_Food_Portions"] / monthly["Total_Food_Portions"]
    monthly["SW_EnergyDensity"] = (
        monthly["Weighted_EnergyDensity_Sum"] / monthly["Mapped_Food_Portions"]
    )
    monthly = monthly[
        [
            "YearMonth",
            "Total_Food_Portions",
            "Mapped_Food_Portions",
            "Coverage_Rate",
            "SW_EnergyDensity",
            "Mapped_Rows",
        ]
    ]

    exclusion_log = (
        food_sales.groupby("Mapping_Status")
        .agg(Rows=("Order ID", "size"), Portions=("Quantity", "sum"))
        .reset_index()
    )
    exclusion_log["Reason"] = exclusion_log["Mapping_Status"].map(STATUS_REASON)
    exclusion_log["Row_Share"] = exclusion_log["Rows"] / len(food_sales)
    exclusion_log["Portion_Share"] = exclusion_log["Portions"] / food_sales["Quantity"].sum()

    unknown_detail = (
        food_sales[food_sales["Item"] == "Unknown"]
        .groupby(["Category", "Price", "Mapping_Status", "Mapped_Item"])
        .agg(Rows=("Order ID", "size"), Portions=("Quantity", "sum"))
        .reset_index()
        .sort_values(["Mapping_Status", "Category", "Price"])
    )
    unknown_detail["Reason"] = unknown_detail["Mapping_Status"].map(STATUS_REASON)

    order_level = food_sales[
        [
            "Order ID",
            "Order Date",
            "YearMonth",
            "Category",
            "Item",
            "Mapped_Item",
            "Price",
            "Quantity",
            "Energy_kcal_per_100g",
            "Weighted_EnergyDensity",
            "Mapping_Status",
        ]
    ].copy()
    order_level = order_level.rename(
        columns={
            "Item": "Original_Item",
            "Energy_kcal_per_100g": "USDA_Energy_kcal_per_100g",
        }
    )

    item_coverage = (
        food_sales.groupby(["Item", "Category", "Mapping_Status"])
        .agg(Rows=("Order ID", "size"), Portions=("Quantity", "sum"))
        .reset_index()
        .sort_values(["Mapping_Status", "Category", "Item"])
    )
    item_coverage["Reason"] = item_coverage["Mapping_Status"].map(STATUS_REASON)

    summary = {
        "source_sales_file": str(SALES_PATH),
        "output_definition": "Monthly Sales-Weighted Estimated Food Energy Density (SW_EnergyDensity)",
        "dv_formula": "sum(USDA comparable-food kcal/100g * Quantity) / sum(Quantity), for included mapped food portions",
        "included_scope": "Food items only; drinks excluded. Vegetarian Platter and ambiguous unknown food records excluded from main DV.",
        "mapped_food_items": int((mapping["Inclusion_Decision"] == "Include").sum()),
        "excluded_mapping_items": mapping.loc[
            mapping["Inclusion_Decision"] != "Include", "Bistro_Item"
        ].tolist(),
        "total_food_rows": int(len(food_sales)),
        "total_food_portions": int(food_sales["Quantity"].sum()),
        "mapped_rows": int(len(mapped_sales)),
        "mapped_portions": int(mapped_sales["Quantity"].sum()),
        "overall_coverage_rate": float(mapped_sales["Quantity"].sum() / food_sales["Quantity"].sum()),
        "monthly_sw_energy_density_mean": float(monthly["SW_EnergyDensity"].mean()),
        "monthly_sw_energy_density_min": float(monthly["SW_EnergyDensity"].min()),
        "monthly_sw_energy_density_max": float(monthly["SW_EnergyDensity"].max()),
    }

    outputs = {
        "summary": summary,
        "metadata": [
            {
                "Table_or_Variable": "USDA Item Mapping",
                "Meaning": "One row per Bistro food item, showing the USDA comparable food used to assign kcal per 100g.",
                "Source_or_Method": "USDA FoodData Central FNDDS 2021-2023; manually audited comparable-food mapping.",
            },
            {
                "Table_or_Variable": "Order-Level Energy Data",
                "Meaning": "One row per food order record after item recovery/exclusion rules and USDA energy-density assignment.",
                "Source_or_Method": "The Bistro sales data merged with the USDA Item Mapping table by item name.",
            },
            {
                "Table_or_Variable": "Monthly DV",
                "Meaning": "One row per month; dependent variable measuring whether monthly food sales shifted toward higher/lower energy-density foods.",
                "Source_or_Method": "sum(USDA kcal/100g * Quantity) / sum(Quantity) for included mapped food portions.",
            },
            {
                "Table_or_Variable": "SW_EnergyDensity",
                "Meaning": "Monthly Sales-Weighted Estimated Food Energy Density; unit is kcal/100g-equivalent.",
                "Source_or_Method": "Derived dependent variable used for modelling.",
            },
            {
                "Table_or_Variable": "Mapping_Status",
                "Meaning": "Explains whether a food order row was directly mapped, recovered via Category+Price, or excluded from the main DV.",
                "Source_or_Method": "Generated by reproducible Python cleaning rules.",
            },
            {
                "Table_or_Variable": "Rows",
                "Meaning": "Number of food-order records. In the Bistro data, one row is one order record for a menu item.",
                "Source_or_Method": "Count of Order ID rows after excluding Drinks from the food-energy analysis.",
            },
            {
                "Table_or_Variable": "Portions",
                "Meaning": "Total number of sold portions, calculated as the sum of the Quantity column. One order row can contain 1-5 portions.",
                "Source_or_Method": "Sum of Quantity in the Bistro sales data.",
            },
            {
                "Table_or_Variable": "Portion_Share",
                "Meaning": "The share of total food portions represented by each mapping/inclusion status.",
                "Source_or_Method": "Portions for a status divided by total food portions.",
            },
            {
                "Table_or_Variable": "Vegetarian Platter",
                "Meaning": "Excluded from main DV because the dish name does not specify ingredients or composition.",
                "Source_or_Method": "No defensible direct USDA comparable food without guessing recipe composition.",
            },
            {
                "Table_or_Variable": "Drinks",
                "Meaning": "Excluded because the DV measures food energy-density preference rather than beverage/hydration choice.",
                "Source_or_Method": "Research design decision.",
            },
        ],
        "mapping_table": mapping.to_dict(orient="records"),
        "order_level_energy_data": order_level.to_dict(orient="records"),
        "monthly_dv": monthly.to_dict(orient="records"),
        "exclusion_log": exclusion_log.to_dict(orient="records"),
        "unknown_detail": unknown_detail.to_dict(orient="records"),
        "item_coverage": item_coverage.to_dict(orient="records"),
    }

    (OUTPUT_DIR / "energy_mapping_outputs.json").write_text(
        json.dumps(clean_for_json(outputs), indent=2), encoding="utf-8"
    )
    mapping.to_csv(OUTPUT_DIR / "usda_mapping_table.csv", index=False)
    order_level.to_csv(OUTPUT_DIR / "order_level_energy_data.csv", index=False)
    monthly.to_csv(OUTPUT_DIR / "monthly_sw_energy_density.csv", index=False)
    exclusion_log.to_csv(OUTPUT_DIR / "mapping_exclusion_log.csv", index=False)
    unknown_detail.to_csv(OUTPUT_DIR / "unknown_detail.csv", index=False)
    item_coverage.to_csv(OUTPUT_DIR / "item_coverage.csv", index=False)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
