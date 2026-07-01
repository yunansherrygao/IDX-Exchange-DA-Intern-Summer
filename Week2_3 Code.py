import pandas as pd
from pathlib import Path
from datetime import date


# Folder that contains the monthly MLS sold CSV files
data_folder = Path("/Users/yunangao/Desktop/IDX Exchange")

# Folder for small EDA output tables
script_folder = Path(__file__).resolve().parent
output_folder = script_folder / "week2_3_outputs"
output_folder.mkdir(exist_ok=True)

# Change this to True when you are ready to save the filtered sold dataset.
save_filtered_csv = False

start_month = "202401"

today = date.today()
if today.month == 1:
    most_recent_completed_month = f"{today.year - 1}12"
else:
    most_recent_completed_month = f"{today.year}{today.month - 1:02d}"


# Find the latest sold month actually available in the data folder.
available_months = []
for file_path in data_folder.glob("CRMLSSold*.csv"):
    month = file_path.stem.replace("CRMLSSold", "").replace("_filled", "")
    if month.isdigit() and len(month) == 6:
        available_months.append(month)

latest_available_month = max(available_months)
end_month = min(most_recent_completed_month, latest_available_month)

print(f"Most recently completed month: {most_recent_completed_month}")
print(f"Latest available sold file month: {latest_available_month}")
print(f"Using date range: {start_month} to {end_month}")


# Build the list of required months
months = pd.period_range(start=start_month, end=end_month, freq="M").strftime("%Y%m")


sold_dfs = []
sold_files_used = []

for month in months:
    filled_file = data_folder / f"CRMLSSold{month}_filled.csv"
    normal_file = data_folder / f"CRMLSSold{month}.csv"

    # Use the filled file when it exists so completed lat/long values are included.
    if filled_file.exists():
        file_path = filled_file
    else:
        file_path = normal_file

    if not file_path.exists():
        print(f"Missing sold file for {month}")
        continue

    sold_month = pd.read_csv(file_path, low_memory=False)
    print(f"Sold {file_path.name}: {len(sold_month):,} rows before concatenation")

    sold_dfs.append(sold_month)
    sold_files_used.append(file_path.name)

sold_rows_before_concat = sum(len(df) for df in sold_dfs)
sold = pd.concat(sold_dfs, ignore_index=True)
sold_rows_after_concat = len(sold)

print("\nSold files used:")
print(sold_files_used)
print(f"Sold total rows before concatenation: {sold_rows_before_concat:,}")
print(f"Sold rows after concatenation: {sold_rows_after_concat:,}")
print(f"Sold columns after concatenation: {sold.shape[1]:,}")


# Drop extra columns from filled files
sold.drop(columns=["lonfilled", "latfilled"], inplace=True, errors="ignore")


print("\nDataset structure before Residential filter:")
print(f"Rows: {sold.shape[0]:,}")
print(f"Columns: {sold.shape[1]:,}")

column_types = sold.dtypes.reset_index()
column_types.columns = ["Column", "DataType"]
column_types.to_csv(output_folder / "sold_column_data_types.csv", index=False)

print("\nColumn data types:")
print(column_types)


property_type_summary = (
    sold["PropertyType"]
    .value_counts(dropna=False)
    .reset_index()
)
property_type_summary.columns = ["PropertyType", "RowCount"]
property_type_summary["Percent"] = (
    property_type_summary["RowCount"] / len(sold) * 100
)
property_type_summary.to_csv(
    output_folder / "sold_property_type_summary.csv",
    index=False,
)

print("\nUnique property types and counts:")
print(property_type_summary)


rows_before_filter = len(sold)
sold_residential = sold[
    sold["PropertyType"].astype(str).str.strip() == "Residential"
].copy()
rows_after_filter = len(sold_residential)

print("\nResidential filtering logic:")
print('Kept records where PropertyType == "Residential"')
print(f"Rows before Residential filter: {rows_before_filter:,}")
print(f"Rows after Residential filter: {rows_after_filter:,}")
print(f"Rows removed: {rows_before_filter - rows_after_filter:,}")

null_summary = pd.DataFrame({
    "Column": sold_residential.columns,
    "MissingCount": sold_residential.isna().sum().values,
})
null_summary["MissingPercent"] = (
    null_summary["MissingCount"] / len(sold_residential) * 100
)
null_summary = null_summary.sort_values(
    by="MissingPercent",
    ascending=False,
)
null_summary["Above90PercentMissing"] = null_summary["MissingPercent"] > 90

high_missing_columns = null_summary[
    null_summary["Above90PercentMissing"]
].copy()

core_fields = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
    "CloseDate",
    "ListingContractDate",
    "CountyOrParish",
    "City",
    "PropertyType",
]

high_missing_columns["DropRecommendation"] = high_missing_columns["Column"].apply(
    lambda col: "Retain core field" if col in core_fields else "Consider dropping"
)

null_summary.to_csv(output_folder / "sold_null_count_summary.csv", index=False)
high_missing_columns.to_csv(
    output_folder / "sold_high_missing_columns_over_90_percent.csv",
    index=False,
)

print("\nMissing value summary:")
print(null_summary)

print("\nColumns above 90% missing:")
print(high_missing_columns)


numeric_fields = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
]

numeric_fields = [
    col for col in numeric_fields if col in sold_residential.columns
]

numeric_summary = (
    sold_residential[numeric_fields]
    .apply(pd.to_numeric, errors="coerce")
    .describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    .T
)

numeric_summary = numeric_summary[
    ["min", "max", "mean", "50%", "1%", "5%", "25%", "75%", "95%", "99%"]
]
numeric_summary = numeric_summary.rename(columns={"50%": "median"})
numeric_summary.to_csv(output_folder / "sold_numeric_distribution_summary.csv")

print("\nNumeric distribution summary:")
print(numeric_summary)


# Required deliverable summary for ClosePrice, LivingArea, and DaysOnMarket
required_numeric_fields = ["ClosePrice", "LivingArea", "DaysOnMarket"]
required_numeric_summary = numeric_summary.loc[
    [col for col in required_numeric_fields if col in numeric_summary.index]
]
required_numeric_summary.to_csv(
    output_folder / "sold_required_numeric_summary.csv"
)

print("\nRequired numeric summary:")
print(required_numeric_summary)


residential_share = rows_after_filter / rows_before_filter * 100
average_close_price = pd.to_numeric(
    sold_residential["ClosePrice"],
    errors="coerce",
).mean()
median_close_price = pd.to_numeric(
    sold_residential["ClosePrice"],
    errors="coerce",
).median()

print("\nSuggested EDA answers:")
print(f"Residential share: {residential_share:.2f}%")
print(f"Average close price: ${average_close_price:,.2f}")
print(f"Median close price: ${median_close_price:,.2f}")

if "ListPrice" in sold_residential.columns and "ClosePrice" in sold_residential.columns:
    close_price = pd.to_numeric(sold_residential["ClosePrice"], errors="coerce")
    list_price = pd.to_numeric(sold_residential["ListPrice"], errors="coerce")
    valid_price_rows = close_price.notna() & list_price.notna() & (list_price > 0)

    sold_above_list = (close_price[valid_price_rows] > list_price[valid_price_rows]).mean() * 100
    sold_below_list = (close_price[valid_price_rows] < list_price[valid_price_rows]).mean() * 100
    sold_at_list = (close_price[valid_price_rows] == list_price[valid_price_rows]).mean() * 100

    print(f"Sold above list price: {sold_above_list:.2f}%")
    print(f"Sold below list price: {sold_below_list:.2f}%")
    print(f"Sold at list price: {sold_at_list:.2f}%")

if "CloseDate" in sold_residential.columns and "ListingContractDate" in sold_residential.columns:
    close_date = pd.to_datetime(sold_residential["CloseDate"], errors="coerce")
    listing_date = pd.to_datetime(
        sold_residential["ListingContractDate"],
        errors="coerce",
    )

    date_issue_count = (close_date < listing_date).sum()
    print(f"Rows where CloseDate is before ListingContractDate: {date_issue_count:,}")

if "CountyOrParish" in sold_residential.columns and "ClosePrice" in sold_residential.columns:
    county_median_prices = (
        sold_residential.assign(
            ClosePriceNumeric=pd.to_numeric(
                sold_residential["ClosePrice"],
                errors="coerce",
            )
        )
        .groupby("CountyOrParish")["ClosePriceNumeric"]
        .median()
        .sort_values(ascending=False)
        .head(10)
    )

    county_median_prices.to_csv(
        output_folder / "top_counties_by_median_close_price.csv"
    )

    print("\nTop counties by median close price:")
    print(county_median_prices)


filtered_output = data_folder / f"Sold_Residential_Filtered_{start_month}_{end_month}.csv"

if save_filtered_csv:
    sold_residential.to_csv(filtered_output, index=False)
    print(f"\nSaved filtered Residential sold dataset to: {filtered_output}")

print("\nWeeks 2-3 EDA script complete.")
print(f"Small EDA report tables saved to: {output_folder.resolve()}")
