import pandas as pd
import geopandas as gpd
from pathlib import Path


data_folder = Path("/Users/yunangao/Desktop/IDX Exchange")
code_folder = Path("/Users/yunangao/Desktop/IDX Exchange Code")

input_file = data_folder / "Sold_Residential_With_Mortgage_Rates_202401_202605.csv"
district_file = Path("/Users/yunangao/Desktop/DistrictAreas2526_-284845464123469011.geojson")

output_file = data_folder / "Sold_Residential_Week6_Features_With_Districts_202401_202605.csv"
sample_output_file = data_folder / "Week6_Engineered_Metrics_Sample.csv"
county_summary_file = data_folder / "Week6_County_Segment_Summary.csv"
property_summary_file = data_folder / "Week6_PropertyType_SubType_Summary.csv"
area_summary_file = data_folder / "Week6_County_MLSArea_Summary.csv"
office_summary_file = data_folder / "Week6_Office_Segment_Summary.csv"
district_summary_file = data_folder / "Week6_School_District_Summary.csv"

sold = pd.read_csv(input_file, low_memory=False)

print(f"Rows loaded: {len(sold):,}")
print(f"Columns loaded: {sold.shape[1]:,}")

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
    "DaysOnMarket",
    "Latitude",
    "Longitude",
]

for column in numeric_columns:
    sold[column] = pd.to_numeric(sold[column], errors="coerce")

valid_numeric_filter = (
    (sold["ClosePrice"] > 0)
    & (sold["ListPrice"] > 0)
    & (sold["OriginalListPrice"] > 0)
    & (sold["LivingArea"] > 0)
    & (sold["DaysOnMarket"] >= 0)
)

rows_before_filter = len(sold)
sold = sold[valid_numeric_filter].copy()

print(f"Rows after metric-ready numeric filter: {len(sold):,}")
print(f"Rows removed before feature engineering: {rows_before_filter - len(sold):,}")

sold["price_ratio"] = sold["ClosePrice"] / sold["ListPrice"]
sold["close_to_original_list_ratio"] = sold["ClosePrice"] / sold["OriginalListPrice"]
sold["price_per_sqft"] = sold["ClosePrice"] / sold["LivingArea"]
sold["days_on_market"] = sold["DaysOnMarket"]
sold["YrMo"] = sold["CloseDate"].dt.to_period("M").astype(str)
sold["listing_to_contract_days"] = (
    sold["PurchaseContractDate"] - sold["ListingContractDate"]
).dt.days
sold["contract_to_close_days"] = (
    sold["CloseDate"] - sold["PurchaseContractDate"]
).dt.days

districts = gpd.read_file(district_file)
unified_districts = districts[districts["DistrictType"] == "Unified"].copy()

valid_geo = (
    sold["Latitude"].notna()
    & sold["Longitude"].notna()
    & (sold["Latitude"] != 0)
    & (sold["Longitude"] != 0)
    & (sold["Longitude"] < 0)
)

properties_geo = gpd.GeoDataFrame(
    sold.loc[valid_geo, ["Latitude", "Longitude"]],
    geometry=gpd.points_from_xy(
        sold.loc[valid_geo, "Longitude"],
        sold.loc[valid_geo, "Latitude"],
    ),
    crs="EPSG:4326",
)

properties_geo = properties_geo.to_crs(unified_districts.crs)

district_join = gpd.sjoin(
    properties_geo,
    unified_districts[["DistrictName", "geometry"]],
    how="left",
    predicate="within",
)

sold["UnifiedSchoolDistrict"] = pd.NA
sold.loc[district_join.index, "UnifiedSchoolDistrict"] = district_join["DistrictName"]

metric_columns = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "price_ratio",
    "close_to_original_list_ratio",
    "price_per_sqft",
    "days_on_market",
    "YrMo",
    "listing_to_contract_days",
    "contract_to_close_days",
    "UnifiedSchoolDistrict",
]

sample_output = sold[metric_columns].head(10)
sample_output.to_csv(sample_output_file, index=False)

county_summary = (
    sold.groupby("CountyOrParish")
    .agg(
        transactions=("ListingKey", "count"),
        median_close_price=("ClosePrice", "median"),
        average_close_price=("ClosePrice", "mean"),
        median_ppsf=("price_per_sqft", "median"),
        median_days_on_market=("days_on_market", "median"),
        median_price_ratio=("price_ratio", "median"),
    )
    .reset_index()
    .sort_values("transactions", ascending=False)
)

property_summary = (
    sold.groupby(["PropertyType", "PropertySubType"], dropna=False)
    .agg(
        transactions=("ListingKey", "count"),
        median_close_price=("ClosePrice", "median"),
        median_ppsf=("price_per_sqft", "median"),
        median_days_on_market=("days_on_market", "median"),
    )
    .reset_index()
    .sort_values("transactions", ascending=False)
)

area_summary = (
    sold.groupby(["CountyOrParish", "MLSAreaMajor"], dropna=False)
    .agg(
        transactions=("ListingKey", "count"),
        median_close_price=("ClosePrice", "median"),
        median_ppsf=("price_per_sqft", "median"),
        median_days_on_market=("days_on_market", "median"),
    )
    .reset_index()
    .sort_values("transactions", ascending=False)
)

office_summary = (
    sold.groupby(["ListOfficeName", "BuyerOfficeName"], dropna=False)
    .agg(
        transactions=("ListingKey", "count"),
        median_close_price=("ClosePrice", "median"),
        median_price_ratio=("price_ratio", "median"),
        median_days_on_market=("days_on_market", "median"),
    )
    .reset_index()
    .sort_values("transactions", ascending=False)
)

district_summary = (
    sold.groupby("UnifiedSchoolDistrict", dropna=False)
    .agg(
        transactions=("ListingKey", "count"),
        median_close_price=("ClosePrice", "median"),
        median_ppsf=("price_per_sqft", "median"),
        median_days_on_market=("days_on_market", "median"),
    )
    .reset_index()
    .sort_values("transactions", ascending=False)
)

sold.to_csv(output_file, index=False)
county_summary.to_csv(county_summary_file, index=False)
property_summary.to_csv(property_summary_file, index=False)
area_summary.to_csv(area_summary_file, index=False)
office_summary.to_csv(office_summary_file, index=False)
district_summary.to_csv(district_summary_file, index=False)

print("\nEngineered metric sample:")
print(sample_output)

print("\nCounty segment summary:")
print(county_summary.head(10))

print("\nSchool district join summary:")
print(f"Unified districts loaded: {len(unified_districts):,}")
print(f"Properties with valid coordinates: {valid_geo.sum():,}")
print(f"Properties matched to a Unified School District: {sold['UnifiedSchoolDistrict'].notna().sum():,}")
print(f"Properties not matched to a Unified School District: {sold['UnifiedSchoolDistrict'].isna().sum():,}")

print("\nSaved files:")
print(output_file)
print(sample_output_file)
print(county_summary_file)
print(property_summary_file)
print(area_summary_file)
print(office_summary_file)
print(district_summary_file)
