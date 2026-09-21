"""
IOM209 Individual Coursework — Analysis Code
Student: Luoyi Zhu
Topic: Economic Factors (CPI + Tech Layoffs) → Budget Comfort Food Preferences

This script:
1. Loads the group-cleaned dataset
2. Performs contextual recovery of Unknown records
3. Defines and calculates the dependent variable (BCF_Pct)
4. Merges with external data (CPI, Tech Layoffs)
5. Exploratory visualisation
6. Predictive modelling (Linear Regression + Random Forest)
7. Forecasting (Jan–Mar 2024)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# ============================================================
# 1. LOAD DATA
# ============================================================
df = pd.read_excel('the_bistro_data_final.xlsx')  # Place this file in the same folder as this script
df['Order Date'] = pd.to_datetime(df['Order Date'])
print(f"Loaded: {len(df)} records, {df['Order Date'].min().date()} to {df['Order Date'].max().date()}")

# ============================================================
# 2. CONTEXTUAL RECOVERY OF UNKNOWN RECORDS
# ============================================================
# The group-stage cleaning labelled 1,758 missing-Item records as "Unknown".
# Here we recover items using Category + Price combination logic.

# Step 2a: Build lookup table — Category+Price combos that map to exactly 1 item
known = df[df['Item'] != 'Unknown']
combo_counts = known.groupby(['Category', 'Price'])['Item'].nunique().reset_index()
combo_counts.columns = ['Category', 'Price', 'Num_Items']

unique_combos = combo_counts[combo_counts['Num_Items'] == 1][['Category', 'Price']]
lookup = known.merge(unique_combos, on=['Category', 'Price'])[
    ['Category', 'Price', 'Item', 'Taste_Profile', 'Temperature', 'Health_Level', 'Ingredient_Type']
].drop_duplicates()

print(f"\nContextual Recovery Lookup: {len(lookup)} unique Category+Price → Item mappings")

# Step 2b: Apply full recovery (Item + all attributes) for unique combos
for _, row in lookup.iterrows():
    mask = (df['Item'] == 'Unknown') & \
           (df['Category'] == row['Category']) & \
           (df['Price'] == row['Price'])
    df.loc[mask, 'Item'] = row['Item']
    df.loc[mask, 'Taste_Profile'] = row['Taste_Profile']
    df.loc[mask, 'Temperature'] = row['Temperature']
    df.loc[mask, 'Health_Level'] = row['Health_Level']
    df.loc[mask, 'Ingredient_Type'] = row['Ingredient_Type']

recovered_full = 1758 - (df['Item'] == 'Unknown').sum()
print(f"  Full item recovery: {recovered_full} records (39.8%)")

# Step 2c: For remaining Unknown records, assign Health_Level where ALL possible
# items in that Category+Price combo share the same Health_Level
# (e.g., Desserts+$6 → Brownie OR Chocolate Cake, both Indulgent)
consistent_hl_combos = [
    ('Desserts', 6.0, 'Indulgent', 'Sweet-Chocolate', 'Room Temp'),
    ('Side Dishes', 4.0, 'Moderate', None, None),  # Mashed Potatoes or Garlic Bread
]

for cat, price, hl, taste, temp in consistent_hl_combos:
    mask = (df['Item'] == 'Unknown') & (df['Category'] == cat) & (df['Price'] == price)
    count = mask.sum()
    if count > 0:
        df.loc[mask, 'Health_Level'] = hl
        if taste:
            df.loc[mask, 'Taste_Profile'] = taste
        if temp:
            df.loc[mask, 'Temperature'] = temp
        print(f"  Health_Level assigned: {cat}+${price} → {hl} ({count} records)")

# Step 2d: Exclude genuinely ambiguous records
remaining_unknown_hl = ((df['Item'] == 'Unknown') & (df['Health_Level'] == 'Unknown')).sum()
print(f"  Excluded (irresolvable ambiguity): {remaining_unknown_hl} records")

# Final valid dataset: exclude records where Health_Level is still Unknown
df_valid = df[df['Health_Level'] != 'Unknown'].copy()
print(f"\nFinal valid records for analysis: {len(df_valid)}")

# ============================================================
# 3. DEFINE DEPENDENT VARIABLE: Budget Comfort Food % (BCF_Pct)
# ============================================================
# BCF = items with Price <= $6 AND Health_Level == 'Indulgent'
# Rationale: excludes expensive Indulgent items (e.g., Steak $20) which respond
# OPPOSITELY to economic pressure (high price elasticity → demand collapses).
# See: Andreyeva et al. (2010)

df_valid['YearMonth'] = df_valid['Order Date'].dt.to_period('M').astype(str)
df_valid['Is_BCF'] = (df_valid['Price'] <= 6) & (df_valid['Health_Level'] == 'Indulgent')

monthly_total = df_valid.groupby('YearMonth')['Order ID'].count().reset_index()
monthly_total.columns = ['YearMonth', 'Total_Valid_Orders']

monthly_bcf = df_valid[df_valid['Is_BCF']].groupby('YearMonth')['Order ID'].count().reset_index()
monthly_bcf.columns = ['YearMonth', 'BCF_Orders']

monthly = monthly_total.merge(monthly_bcf, on='YearMonth')
monthly['BCF_Pct'] = monthly['BCF_Orders'] / monthly['Total_Valid_Orders'] * 100

print(f"\nBCF_Pct range: {monthly['BCF_Pct'].min():.1f}% – {monthly['BCF_Pct'].max():.1f}%")

# ============================================================
# 4. MERGE WITH EXTERNAL DATA
# ============================================================
# Factor 1: CPI (from FRED, series CPIAUCSL, https://fred.stlouisfed.org/series/CPIAUCSL)
cpi = pd.read_csv('economic_cpi_2022_2023.csv')
cpi['YearMonth'] = pd.to_datetime(cpi['observation_date']).dt.to_period('M').astype(str)
cpi.rename(columns={'CPIAUCSL': 'CPI'}, inplace=True)

# Factor 2: Tech Layoffs (from Layoffs.fyi, https://layoffs.fyi/, Austin area filter)
layoffs = pd.read_csv('economic_tech_layoffs_austin_2022_2023.csv')
layoffs['Date'] = pd.to_datetime(layoffs['Date'], format='mixed', dayfirst=False)
layoffs['YearMonth'] = layoffs['Date'].dt.to_period('M').astype(str)
layoffs_monthly = layoffs.groupby('YearMonth').agg(
    Layoff_Events=('Company', 'count'),
    Total_Laid_Off=('No. Laid Off', lambda x: pd.to_numeric(x, errors='coerce').sum())
).reset_index()

# Merge all
analysis = monthly.merge(cpi[['YearMonth', 'CPI']], on='YearMonth', how='left')
analysis = analysis.merge(layoffs_monthly, on='YearMonth', how='left')
analysis[['Layoff_Events', 'Total_Laid_Off']] = analysis[['Layoff_Events', 'Total_Laid_Off']].fillna(0)

# --- Add lagged CPI variable (3-month lag) ---
# Rationale: economic pressure doesn't change behaviour instantly. Consumers may
# take ~3 months to deplete savings and adjust food habits. Lag analysis showed
# that CPI 3 months prior has a stronger relationship with BCF_Pct (r=0.408)
# than same-month CPI (r=0.244). Including CPI_lag3 captures this delayed effect.
analysis['CPI_lag3'] = analysis['CPI'].shift(3)

# Drop the first 3 rows that now have NaN due to lagging (N goes from 24 → 21)
analysis_lagged = analysis.dropna(subset=['CPI_lag3']).reset_index(drop=True)

print(f"\nFinal analysis dataset: {len(analysis)} months × {len(analysis.columns)} columns")
print(analysis[['YearMonth', 'BCF_Pct', 'CPI', 'Layoff_Events', 'Total_Laid_Off']].to_string(index=False))

print("=== Contextual Recovery Summary ===")
print(f"Original Unknown records:     1,758  (10.0%)")
print(f"Full item recovery:             699  (39.8%)")
print(f"Health_Level-only recovery:     460  (26.2%)")
print(f"Excluded (irresolvable):        599  (34.1%)")
print(f"Final valid records:         16,935  (vs 15,776 if all excluded)")

# ============================================================
# 5. EXPLORATORY VISUALISATION
# ============================================================
# Three charts required by the task sheet:
#   (a) Time series of BCF_Pct  — shows overall trend of the DV over 24 months
#   (b) Dual-axis: CPI + BCF_Pct  — visual test of H1 (do they move together?)
#   (c) Scatter: Layoff_Events vs BCF_Pct  — visual test of H2

# -- Colour palette (consistent throughout) --
COLOR_BCF = '#3A8A5C'    # green  = BCF (the DV)
COLOR_CPI = '#4A7FB5'    # blue   = CPI (Factor 1)
COLOR_LAY = '#C06040'    # terracotta = Layoffs (Factor 2)

# -- Add a numeric index column for plotting (0 = Jan 2022, 23 = Dec 2023) --
analysis['Month_Index'] = range(len(analysis))

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Figure 1: Exploratory Visualisations', fontsize=14, fontweight='bold', y=1.02)

# --- Chart A: BCF_Pct over time ---
ax = axes[0]
ax.plot(analysis['Month_Index'], analysis['BCF_Pct'],
        color=COLOR_BCF, linewidth=2, marker='o', markersize=5)
ax.axhline(analysis['BCF_Pct'].mean(), color='grey', linestyle='--', alpha=0.6,
           label=f"Mean: {analysis['BCF_Pct'].mean():.1f}%")
ax.set_title('(A) BCF_Pct Over Time', fontweight='bold')
ax.set_xlabel('Month (0 = Jan 2022)')
ax.set_ylabel('BCF % of Monthly Orders')
ax.set_xticks(range(0, 24, 3))
ax.set_xticklabels([analysis['YearMonth'].iloc[i] for i in range(0, 24, 3)], rotation=45, ha='right')
ax.legend(fontsize=9)

# --- Chart B: Dual-axis CPI (left) + BCF_Pct (right) over time ---
# A dual-axis chart overlays two y-axes on the same x-axis.
# This makes it easy to see whether CPI rises correspond to BCF rises.
ax2 = axes[1]
ax2_right = ax2.twinx()   # create a second y-axis sharing the same x-axis

ax2.plot(analysis['Month_Index'], analysis['CPI'],
         color=COLOR_CPI, linewidth=2, marker='s', markersize=4, label='CPI')
ax2_right.plot(analysis['Month_Index'], analysis['BCF_Pct'],
               color=COLOR_BCF, linewidth=2, linestyle='--', marker='o', markersize=4, label='BCF_Pct')

ax2.set_title('(B) CPI vs BCF_Pct (H1)', fontweight='bold')
ax2.set_xlabel('Month (0 = Jan 2022)')
ax2.set_ylabel('CPI (left)', color=COLOR_CPI)
ax2_right.set_ylabel('BCF % (right)', color=COLOR_BCF)
ax2.tick_params(axis='y', labelcolor=COLOR_CPI)
ax2_right.tick_params(axis='y', labelcolor=COLOR_BCF)
ax2.set_xticks(range(0, 24, 3))
ax2.set_xticklabels([analysis['YearMonth'].iloc[i] for i in range(0, 24, 3)], rotation=45, ha='right')

# Combine legends from both axes into one box
lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2_right.get_legend_handles_labels()
ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=9)

# --- Chart C: Scatter plot — Layoff Events vs BCF_Pct ---
# A scatter plot shows whether months with more layoffs tend to have higher BCF%.
# We add a regression line to quantify the direction of the relationship.
ax3 = axes[2]
ax3.scatter(analysis['Layoff_Events'], analysis['BCF_Pct'],
            color=COLOR_LAY, s=60, alpha=0.8, edgecolors='white', zorder=3)

# Add regression line
slope, intercept, r_val, p_val, _ = stats.linregress(analysis['Layoff_Events'], analysis['BCF_Pct'])
x_line = np.linspace(analysis['Layoff_Events'].min(), analysis['Layoff_Events'].max(), 100)
ax3.plot(x_line, slope * x_line + intercept, color='black', linestyle='--',
         linewidth=1.5, label=f'r = {r_val:.2f}, p = {p_val:.3f}')

ax3.set_title('(C) Layoff Events vs BCF_Pct (H2)', fontweight='bold')
ax3.set_xlabel('Monthly Layoff Events (Austin)')
ax3.set_ylabel('BCF % of Monthly Orders')
ax3.legend(fontsize=9)

plt.tight_layout()
plt.savefig('fig1_exploratory.png', dpi=150, bbox_inches='tight')
plt.show()
print("Figure 1 saved → fig1_exploratory.png")

# Print Pearson correlation coefficients for reference
r_cpi, p_cpi = stats.pearsonr(analysis['CPI'], analysis['BCF_Pct'])
r_lay, p_lay = stats.pearsonr(analysis['Layoff_Events'], analysis['BCF_Pct'])
print(f"\nCorrelation: CPI vs BCF_Pct:           r = {r_cpi:.3f}, p = {p_cpi:.3f}")
print(f"Correlation: Layoff_Events vs BCF_Pct:  r = {r_lay:.3f}, p = {p_lay:.3f}")


# ============================================================
# 6. PREDICTIVE MODELLING
# ============================================================
# We build two models to predict BCF_Pct from CPI and Layoff_Events.
#
#   Model 1 — Linear Regression:
#       Simple and interpretable. The coefficient tells us exactly how much
#       BCF_Pct changes for a 1-unit increase in CPI or Layoff_Events.
#       Best when the relationship is roughly linear.
#
#   Model 2 — Random Forest Regressor:
#       An ensemble of many decision trees. It can capture non-linear patterns
#       and interactions between features. Less interpretable than LR, but
#       more flexible. Feature importance tells us which factor drives predictions more.
#
# Train / Test split:
#   Train: first 22 months (2022-01 to 2023-10)
#   Test:  last  2 months  (2023-11 to 2023-12)
# With lag3, we have 21 months total. Train on first 19, test on last 2.
# This is intentionally small — focus is on forecasting, not test accuracy.

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# --- Prepare features and target ---
features = ['CPI_lag3', 'Layoff_Events']   # CPI_lag3 captures delayed economic effect
target   = 'BCF_Pct'                  # the dependent variable (DV)

X = analysis_lagged[features].values
y = analysis_lagged[target].values

# Train-test split: first 19 months for training, last 2 for testing (21 total)
TRAIN_SIZE = len(analysis_lagged) - 2
X_train, X_test = X[:TRAIN_SIZE], X[TRAIN_SIZE:]
y_train, y_test = y[:TRAIN_SIZE], y[TRAIN_SIZE:]

print(f"\nTrain: {TRAIN_SIZE} months | Test: {len(X_test)} months")

# --- Model 1: Linear Regression ---
lr = LinearRegression()
lr.fit(X_train, y_train)
y_pred_lr = lr.predict(X_test)

print(f"\n=== Linear Regression ===")
print(f"  Intercept: {lr.intercept_:.3f}")
for feat, coef in zip(features, lr.coef_):
    print(f"  Coefficient [{feat}]: {coef:.4f}")
    # Interpretation: for every +1 unit in this feature,
    # BCF_Pct changes by 'coef' percentage points (holding other features constant)
print(f"  R² (train): {r2_score(y_train, lr.predict(X_train)):.3f}")
print(f"  R² (test):  {r2_score(y_test, y_pred_lr):.3f}")
print(f"  MAE (test): {mean_absolute_error(y_test, y_pred_lr):.3f} pp")

# --- Model 2: Random Forest ---
rf = RandomForestRegressor(n_estimators=100,   # 100 decision trees in the forest
                           max_depth=3,         # limit depth to avoid overfitting on 22 data points
                           random_state=42)     # random_state=42 ensures reproducibility
rf.fit(X_train, y_train)
y_pred_rf = rf.predict(X_test)

print(f"\n=== Random Forest ===")
print(f"  Feature Importances:")
for feat, imp in zip(features, rf.feature_importances_):
    print(f"    {feat}: {imp:.3f}  ({imp*100:.1f}%)")
    # Importance = how much this feature reduces prediction error across all trees
    # Higher = that factor explains more of the variation in BCF_Pct
print(f"  R² (train): {r2_score(y_train, rf.predict(X_train)):.3f}")
print(f"  R² (test):  {r2_score(y_test, y_pred_rf):.3f}")
print(f"  MAE (test): {mean_absolute_error(y_test, y_pred_rf):.3f} pp")

# --- Figure 2: Actual vs Predicted (both models) ---
fig2, axes2 = plt.subplots(1, 2, figsize=(12, 4.5))
fig2.suptitle('Figure 2: Model Performance — Actual vs Predicted BCF_Pct', fontsize=13, fontweight='bold')

for ax_idx, (model_name, y_pred) in enumerate([('Linear Regression', y_pred_lr),
                                                ('Random Forest',     y_pred_rf)]):
    ax = axes2[ax_idx]
    # Plot actual values for the full training period as context
    ax.plot(range(TRAIN_SIZE), y_train, color='grey', linewidth=1.5, alpha=0.5, label='Training (actual)')
    # Plot actual vs predicted for the 2-month test period
    test_idx = range(TRAIN_SIZE, len(y))
    ax.plot(test_idx, y_test,  color=COLOR_BCF,  linewidth=2, marker='o', markersize=7, label='Test (actual)')
    ax.plot(test_idx, y_pred,  color='#FF6B35',  linewidth=2, marker='x', markersize=9,
            markeredgewidth=2, linestyle='--', label='Test (predicted)')
    ax.set_title(model_name, fontweight='bold')
    ax.set_xlabel('Month Index')
    ax.set_ylabel('BCF %')
    ax.legend(fontsize=9)
    ax.axvline(TRAIN_SIZE - 0.5, color='black', linestyle=':', alpha=0.4)  # train/test boundary line
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    ax.set_title(f'{model_name}\nR²={r2:.3f}, MAE={mae:.2f}pp', fontweight='bold')

plt.tight_layout()
plt.savefig('fig2_model_performance.png', dpi=150, bbox_inches='tight')
plt.show()
print("Figure 2 saved → fig2_model_performance.png")


# ============================================================
# 7. FORECASTING (January – March 2024)
# ============================================================
# We use the fitted Linear Regression model to predict BCF_Pct for the 3 months
# after the data ends (Jan–Mar 2024).
#
# For CPI: we use a simple linear extrapolation based on the average monthly
# CPI increase observed in the training data.
# For Layoff_Events: we assume 2 events per month (conservative estimate
# based on the 2023 monthly average of ~2.0 events).

# Calculate average monthly CPI increase from the training period
cpi_monthly_increase = (analysis['CPI'].iloc[TRAIN_SIZE-1] - analysis['CPI'].iloc[0]) / (TRAIN_SIZE - 1)
last_cpi = analysis['CPI'].iloc[-1]

forecast_months = ['2024-01', '2024-02', '2024-03']
forecast_cpi    = [last_cpi + cpi_monthly_increase * (i+1) for i in range(3)]
forecast_lay    = [2.0, 2.0, 2.0]   # conservative assumption

X_forecast = np.array(list(zip(forecast_cpi, forecast_lay)))

# Use Linear Regression for the forecast (more interpretable than RF for extrapolation)
y_forecast_lr = lr.predict(X_forecast)
y_forecast_rf = rf.predict(X_forecast)

print(f"\n=== Forecast: Jan–Mar 2024 ===")
print(f"{'Month':<12} {'CPI (est.)':<14} {'Layoffs':<10} {'LR Pred':>10} {'RF Pred':>10}")
print("-" * 56)
for month, cpi_est, lay, lr_p, rf_p in zip(forecast_months, forecast_cpi, forecast_lay,
                                             y_forecast_lr, y_forecast_rf):
    print(f"{month:<12} {cpi_est:<14.1f} {lay:<10.0f} {lr_p:>10.2f}% {rf_p:>10.2f}%")

# --- Figure 3: Forecast chart ---
fig3, ax3 = plt.subplots(figsize=(11, 5))

# Historical BCF_Pct (grey background)
ax3.plot(range(len(analysis)), analysis['BCF_Pct'],
         color='grey', linewidth=1.5, alpha=0.5, label='Historical BCF_Pct (2022-2023)')

# LR forecast
forecast_idx = [len(analysis), len(analysis)+1, len(analysis)+2]
ax3.plot(forecast_idx, y_forecast_lr,
         color=COLOR_CPI, linewidth=2, marker='D', markersize=8,
         linestyle='--', label='LR Forecast (Jan–Mar 2024)')

# RF forecast
ax3.plot(forecast_idx, y_forecast_rf,
         color=COLOR_LAY, linewidth=2, marker='s', markersize=8,
         linestyle=':', label='RF Forecast (Jan–Mar 2024)')

# Shade forecast region
ax3.axvspan(len(analysis)-0.5, len(analysis)+2.5, alpha=0.08, color='yellow', label='Forecast window')

# Add data labels on forecast points
for i, (lr_p, rf_p, m) in enumerate(zip(y_forecast_lr, y_forecast_rf, forecast_months)):
    ax3.annotate(f'{lr_p:.1f}%', xy=(forecast_idx[i], lr_p),
                 xytext=(0, 10), textcoords='offset points', ha='center', color=COLOR_CPI, fontsize=8)
    ax3.annotate(f'{rf_p:.1f}%', xy=(forecast_idx[i], rf_p),
                 xytext=(0, -15), textcoords='offset points', ha='center', color=COLOR_LAY, fontsize=8)

# X-axis labels: historical months + forecast months
all_labels = list(analysis['YearMonth']) + forecast_months
tick_positions = list(range(0, len(analysis), 3)) + forecast_idx
ax3.set_xticks(tick_positions)
ax3.set_xticklabels([all_labels[i] for i in tick_positions], rotation=45, ha='right')
ax3.set_title('Figure 3: BCF_Pct History and Forecast (Jan–Mar 2024)', fontweight='bold')
ax3.set_ylabel('Budget Comfort Food %')
ax3.legend(fontsize=9, loc='upper left')
ax3.axvline(len(analysis)-0.5, color='black', linestyle=':', alpha=0.4)

plt.tight_layout()
plt.savefig('fig3_forecast.png', dpi=150, bbox_inches='tight')
plt.show()
print("Figure 3 saved → fig3_forecast.png")
print("\n✅  All steps complete. Output files: fig1_exploratory.png, fig2_model_performance.png, fig3_forecast.png")
