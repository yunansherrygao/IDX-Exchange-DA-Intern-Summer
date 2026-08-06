import pandas as pd
from pathlib import Path


data_folder = Path("/Users/yunangao/Desktop/IDX Exchange")

input_file = data_folder / "Sold_Residential_Week6_Features_With_Districts_202401_202605.csv"
flagged_output = data_folder / "Week7_Sold_Residential_Full_Flagged_202401_202605.csv"
filtered_output = data_folder / "Week7_Sold_Residential_Filtered_Analysis_202401_202605.csv"
iqr_report_file = data_folder / "Week7_IQR_Threshold_Report.csv"
comparison_file = data_folder / "Week7_Before_After_Comparison.csv"
written_comparison_file = data_folder / "Week7_Written_Comparison.txt"

sold = pd.read_csv(input_file, low_memory=False)

print(f"Rows loaded: {len(sold):,}")
print(f"Columns loaded: {sold.shape[1]:,}")

numeric_fields = [
    "ClosePrice",
    "LivingArea",
    "DaysOnMarket",
    "price_per_sqft",
    "price_ratio",
    "close_to_original_list_ratio",
    "BedroomsTotal",
    "BathroomsTotalInteger",
]

for column in numeric_fields:
    if column in sold.columns:
        sold[column] = pd.to_numeric(sold[column], errors="coerce")

sold["invalid_business_rule_flag"] = (
    (sold["ClosePrice"] <= 0)
    | (sold["LivingArea"] <= 0)
    | (sold["DaysOnMarket"] < 0)
    | (sold["BedroomsTotal"] < 0)
    | (sold["BathroomsTotalInteger"] < 0)
)

iqr_fields = ["ClosePrice", "LivingArea", "DaysOnMarket"]
iqr_report_rows = []

for column in iqr_fields:
    q1 = sold[column].quantile(0.25)
    q3 = sold[column].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    flag_column = f"{column}_iqr_outlier_flag"

    sold[flag_column] = (
        sold[column].notna()
        & ((sold[column] < lower) | (sold[column] > upper))
    )

    iqr_report_rows.append({
        "field": column,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_bound": lower,
        "upper_bound": upper,
        "p01": sold[column].quantile(0.01),
        "p05": sold[column].quantile(0.05),
        "p50": sold[column].quantile(0.50),
        "p95": sold[column].quantile(0.95),
        "p99": sold[column].quantile(0.99),
        "outlier_count": sold[flag_column].sum(),
        "outlier_percent": sold[flag_column].mean() * 100,
    })

sold["any_iqr_outlier_flag"] = sold[
    [f"{column}_iqr_outlier_flag" for column in iqr_fields]
].any(axis=1)

sold["remove_from_analysis_flag"] = (
    sold["invalid_business_rule_flag"]
    | sold["any_iqr_outlier_flag"]
)

filtered_sold = sold[~sold["remove_from_analysis_flag"]].copy()

comparison_rows = []
comparison_fields = ["ClosePrice", "LivingArea", "DaysOnMarket"]

for column in comparison_fields:
    if column in sold.columns:
        comparison_rows.append({
            "field": column,
            "median_before_filtering": sold[column].median(),
            "median_after_filtering": filtered_sold[column].median(),
            "median_change": filtered_sold[column].median() - sold[column].median(),
        })

comparison = pd.DataFrame(comparison_rows)
iqr_report = pd.DataFrame(iqr_report_rows)

sold.to_csv(flagged_output, index=False)
filtered_sold.to_csv(filtered_output, index=False)
iqr_report.to_csv(iqr_report_file, index=False)
comparison.to_csv(comparison_file, index=False)

written_comparison = f"""Week 7 Outlier Detection Comparison

The full flagged dataset preserves all original records and adds outlier flag columns.
The filtered analysis dataset removes records with invalid business-rule values or IQR outliers.

Rows before filtering: {len(sold):,}
Rows after filtering: {len(filtered_sold):,}
Rows removed from analysis dataset: {len(sold) - len(filtered_sold):,}

Median ClosePrice before filtering: ${sold["ClosePrice"].median():,.2f}
Median ClosePrice after filtering: ${filtered_sold["ClosePrice"].median():,.2f}

Median LivingArea before filtering: {sold["LivingArea"].median():,.2f}
Median LivingArea after filtering: {filtered_sold["LivingArea"].median():,.2f}

Median DaysOnMarket before filtering: {sold["DaysOnMarket"].median():,.2f}
Median DaysOnMarket after filtering: {filtered_sold["DaysOnMarket"].median():,.2f}
"""

written_comparison_file.write_text(written_comparison)

print("\nIQR threshold report:")
print(iqr_report)

print("\nBefore and after comparison:")
print(comparison)

print("\nFlag counts:")
print(f"Invalid business-rule rows: {sold['invalid_business_rule_flag'].sum():,}")
print(f"Any IQR outlier rows: {sold['any_iqr_outlier_flag'].sum():,}")
print(f"Rows removed from filtered analysis dataset: {sold['remove_from_analysis_flag'].sum():,}")

print("\nDataset size comparison:")
print(f"Rows before filtering: {len(sold):,}")
print(f"Rows after filtering: {len(filtered_sold):,}")

print("\nSaved files:")
print(flagged_output)
print(filtered_output)
print(iqr_report_file)
print(comparison_file)
print(written_comparison_file)
