# Group-stage record cleaning snapshot

This folder preserves the code and provenance for the earliest data-cleaning
stage that the individual analysis builds on. The notebook and menu lookup were
copied from the IOM209 group repository at commit
[`bb54b7602f41788b283d359a79bd6fad475fe862`](https://github.com/Alex-jjh/ay2526-iom209-restaurant-sales/commit/bb54b7602f41788b283d359a79bd6fad475fe862).
They are included for provenance and reproducibility and should not be read as
work completed solely by the owner of this repository.

## Files

- `step1_restaurant_context.ipynb`: group notebook that profiles missing data,
  fills missing item and payment labels, imputes price and quantity, recalculates
  order totals, derives calendar fields, and adds menu classifications.
- `menu_classification_reference.csv`: lookup table used for the enrichment.

The three customer-level CSV files are not duplicated in this public repository.
They remain available in the linked group repository and have this verified
manifest:

| File in group repository | Rows | Columns | SHA-256 |
|---|---:|---:|---|
| `data/raw/restaurant_sales_data.csv` | 17,534 | 9 | `743c7eb06e5e6ed4b8f48f244ef51afa4d5900c5e7ec959ae26af457b13488d7` |
| `data/cleaned/restaurant_sales_data_cleaned.csv` | 17,534 | 13 | `77930f5d0c128f7bdf5695b138927c0ef7daf9c387d505c0b6b5831f69811cec` |
| `data/cleaned/restaurant_sales_data_enriched.csv` | 17,534 | 17 | `08cf74e0d988b6afa98c3e3d9b5c077a011672c7bc29780d0b26873ff0057021` |

Use `scripts/00_prepare_sales_input.py` at the repository root to turn the
enriched CSV into the local XLSX input expected by the individual pipeline.
The top-level `run_pipeline.py` does not rerun this historical group notebook.
