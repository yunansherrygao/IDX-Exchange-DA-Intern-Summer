import pandas as pd
from pathlib import Path


data_folder = Path("/Users/yunangao/Desktop/IDX Exchange")
input_file = data_folder / "Sold_Residential_With_Mortgage_Rates_202401_202605.csv"
output_file = data_folder / "Sold_Residential_Cleaned_202401_202605.csv"
report_file = data_folder / "Sold_Residential_Cleaning_Report_202401_202605.csv"

sold = pd.read_csv(input_file, low_memory=False)

rows_before = len(sold)
cols_before = sold.shape[1]

print(f"Rows before cleaning: {rows_before:,}")
print(f"Columns before cleaning: {cols_before:,}")

date_columns = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
]

for column in date_columns:
    sold[column] = pd.to_datetime(sold[column], errors="coerce")

numeric_columns = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

for column in numeric_columns:
    if column in sold.columns:
        sold[column] = pd.to_numeric(sold[column], errors="coerce")

metadata_columns_to_drop = [
    "BuyerAgentAOR",
    "ListAgentAOR",
    "ListAgentEmail",
    "ListAgentFirstName",
    "ListAgentLastName",
    "ListAgentFullName",
    "CoListAgentFirstName",
    "CoListAgentLastName",
    "BuyerAgentMlsId",
    "BuyerAgentFirstName",
    "BuyerAgentLastName",
    "CoBuyerAgentFirstName",
    "ListOfficeName",
    "BuyerOfficeName",
    "CoListOfficeName",
    "BuyerOfficeAOR",
    "ElementarySchool",
    "ElementarySchoolDistrict",
    "MiddleOrJuniorSchool",
    "MiddleOrJuniorSchoolDistrict",
    "HighSchool",
    "HighSchoolDistrict",
    "OriginatingSystemName",
    "OriginatingSystemSubName",
    "BuyerAgencyCompensationType",
    "BuyerAgencyCompensation",
]

columns_to_drop = [
    column for column in metadata_columns_to_drop if column in sold.columns
]
sold.drop(columns=columns_to_drop, inplace=True)

sold["listing_after_close_flag"] = sold["ListingContractDate"] > sold["CloseDate"]
sold["purchase_after_close_flag"] = sold["PurchaseContractDate"] > sold["CloseDate"]
sold["negative_timeline_flag"] = (
    sold["PurchaseContractDate"] < sold["ListingContractDate"]
)

sold["missing_coordinate_flag"] = sold["Latitude"].isna() | sold["Longitude"].isna()
sold["zero_coordinate_flag"] = (sold["Latitude"] == 0) | (sold["Longitude"] == 0)
sold["positive_longitude_flag"] = sold["Longitude"] > 0
sold["implausible_coordinate_flag"] = (
    (sold["Latitude"] < 32)
    | (sold["Latitude"] > 42.5)
    | (sold["Longitude"] < -125)
    | (sold["Longitude"] > -114)
)

sold["invalid_numeric_flag"] = (
    (sold["ClosePrice"] <= 0)
    | (sold["LivingArea"] <= 0)
    | (sold["DaysOnMarket"] < 0)
    | (sold["BedroomsTotal"] < 0)
    | (sold["BathroomsTotalInteger"] < 0)
)

categorical_fill_columns = [
    "CountyOrParish",
    "City",
    "PropertySubType",
    "StateOrProvince",
    "PostalCode",
]

for column in categorical_fill_columns:
    if column in sold.columns:
        sold[column] = sold[column].fillna("Unknown")

rows_invalid_numeric = sold["invalid_numeric_flag"].sum()
sold_cleaned = sold[~sold["invalid_numeric_flag"]].copy()

rows_after = len(sold_cleaned)
cols_after = sold_cleaned.shape[1]

dtype_confirmation = sold_cleaned[
    date_columns + [column for column in numeric_columns if column in sold_cleaned.columns]
].dtypes.reset_index()
dtype_confirmation.columns = ["column", "dtype_after_cleaning"]

flag_summary = pd.DataFrame({
    "check": [
        "listing_after_close_flag",
        "purchase_after_close_flag",
        "negative_timeline_flag",
        "missing_coordinate_flag",
        "zero_coordinate_flag",
        "positive_longitude_flag",
        "implausible_coordinate_flag",
        "invalid_numeric_flag_removed",
    ],
    "record_count": [
        sold["listing_after_close_flag"].sum(),
        sold["purchase_after_close_flag"].sum(),
        sold["negative_timeline_flag"].sum(),
        sold["missing_coordinate_flag"].sum(),
        sold["zero_coordinate_flag"].sum(),
        sold["positive_longitude_flag"].sum(),
        sold["implausible_coordinate_flag"].sum(),
        rows_invalid_numeric,
    ],
})

missing_summary = pd.DataFrame({
    "column": sold_cleaned.columns,
    "missing_count_after_cleaning": sold_cleaned.isna().sum().values,
})
missing_summary["missing_percent_after_cleaning"] = (
    missing_summary["missing_count_after_cleaning"] / len(sold_cleaned) * 100
)

cleaning_report = pd.concat(
    [
        pd.DataFrame({
            "item": [
                "rows_before_cleaning",
                "rows_after_cleaning",
                "columns_before_cleaning",
                "columns_after_cleaning",
                "columns_dropped",
            ],
            "value": [
                rows_before,
                rows_after,
                cols_before,
                cols_after,
                ", ".join(columns_to_drop),
            ],
        }),
        flag_summary.rename(columns={"check": "item", "record_count": "value"}),
    ],
    ignore_index=True,
)

sold_cleaned.to_csv(output_file, index=False)
cleaning_report.to_csv(report_file, index=False)
dtype_confirmation.to_csv(
    data_folder / "Sold_Residential_Cleaning_Dtype_Check_202401_202605.csv",
    index=False,
)
missing_summary.to_csv(
    data_folder / "Sold_Residential_Cleaning_Missing_Summary_202401_202605.csv",
    index=False,
)

print(f"Rows after cleaning: {rows_after:,}")
print(f"Columns after cleaning: {cols_after:,}")
print(f"Columns dropped: {len(columns_to_drop)}")
print(f"Rows removed for invalid numeric values: {rows_invalid_numeric:,}")

print("\nDate consistency flag counts:")
print(flag_summary.iloc[:3])

print("\nGeographic data quality summary:")
print(flag_summary.iloc[3:7])

print("\nData type confirmations:")
print(dtype_confirmation)

print(f"\nSaved cleaned dataset to: {output_file}")
print(f"Saved cleaning report to: {report_file}")
