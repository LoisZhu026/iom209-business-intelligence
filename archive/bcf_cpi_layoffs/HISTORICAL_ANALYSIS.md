# Historical BCF and tech-layoffs analysis

This folder preserves an earlier individual-analysis direction recovered from
the local IOM209 Workplace project. It is complete code rather than the shorter
Desktop draft, whose modelling and forecasting sections ended in `TODO`
comments.

This was not the analysis used in the final submitted individual report. The
submitted report uses Energy-Density Preference (EDP) as the target and CPI YoY
plus Austin temperature as predictors. Its production code is in
`scripts/01_build_energy_mapping.py` through `scripts/04_run_models.py`.

## What this historical version does

- Recovers some of the 1,758 records whose item was labelled `Unknown`.
- Defines `BCF_Pct` as the monthly share of valid orders that are indulgent and
  cost no more than $6.
- Merges monthly BCF with CPI and Austin-area technology layoff events.
- Fits Linear Regression and Random Forest models using three-month-lagged CPI
  and layoff-event counts.
- Reports train/test R-squared and test MAE.
- Produces conditional forecasts for January to March 2024 and three figures.

The recovered run produced 16,935 valid records and 21 lagged monthly model
observations. Linear Regression test MAE was 3.324 percentage points and test
R-squared was -0.266; Random Forest test MAE was 3.432 percentage points and
test R-squared was -0.339.

## Reproduce it locally

Customer-level sales data are not stored in this public repository. Place the
group-stage `the_bistro_data_final.xlsx` in this directory, then run:

```bash
python individual_analysis.py
```

The historical forecast block passes extrapolated CPI values to a model fitted
with a lagged-CPI feature. This inconsistency, the two-month test set, and the
final report's decision to use EDP are reasons to treat this folder as an
archived research path rather than the final model.
